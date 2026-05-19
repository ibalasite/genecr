"""Template-driven inverse parser: rendered .md + jinja template → input dict.

Pure deterministic, no AI. Walks the jinja AST and consumes the rendered text
left-to-right, producing a nested dict whose shape mirrors the template's
variable accesses.

Scope (what is supported):
- Output blocks with TemplateData (literal text) and variable references
  (Name / Getattr / Getitem chains).
- For loops over a Name/Getattr path; loop body may contain literals,
  variable references, and nested For/If blocks.
- If blocks (no else / with else) — we try the "true" branch first, fall
  back to skipping (false branch) when the literal anchors don't match.
- Filters and CondExpr (`a if cond else b`) inside an output: treated as
  opaque single capture; we record the value verbatim under a synthetic
  path `_opaque_<n>` (we cannot reverse `length`, `default`, etc.).
- `loop.last` / `loop.index` references: not captured (read-only loop vars).

Anything else raises InverseError. The parser is best-effort against the
existing genecr templates; the test corpus tells us how far we get.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import jinja2
from jinja2 import nodes


class InverseError(Exception):
    pass


class _Backtrack(Exception):
    pass


def _snapshot(d):
    import copy
    return copy.deepcopy(d)


def _restore(target, src):
    target.clear()
    target.update(src)


# ─── Public API ─────────────────────────────────────────────────────────


def md_to_input(template_source: str, md_text: str, schema: dict | None = None) -> dict:
    """Reverse-render template against md_text, returning a nested dict.

    Raises InverseError if the template contains unsupported constructs or
    the md_text doesn't match the template structure.
    """
    env = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    ast = env.parse(template_source)
    parser = _Parser(md_text)
    parser.consume_nodes(ast.body, _Scope())
    # Tail must be fully consumed (allow trailing whitespace).
    if parser.pos < len(md_text) and md_text[parser.pos:].strip():
        raise InverseError(
            f"unconsumed tail at pos {parser.pos}: {md_text[parser.pos:parser.pos+80]!r}"
        )
    if schema:
        import jsonschema
        jsonschema.validate(parser.data, schema)
    return parser.data


# ─── Internals ──────────────────────────────────────────────────────────


@dataclass
class _Scope:
    """Lexical scope mapping loop-var names to (data_list_ref, index)."""
    # Stack of (loop_var_name, list_ref, current_item_dict)
    binds: dict[str, dict] = field(default_factory=dict)
    # Parent path for the currently active loop item, so writes go to right place.
    # binds[var] = the dict we should write fields into.


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.data: dict = {}
        self._opaque_n = 0
        # Stack of outer fallback anchors (longer/loop-exit literals that
        # should also terminate a capture if encountered earlier than the
        # inner stop_literal). Pushed on For/If entry.
        self._fallback_anchors: list[str] = []

    # ── primitive readers ──────────────────────────────────────────────

    def consume_literal(self, literal: str) -> None:
        # Be tolerant of differences in trailing whitespace inside literals:
        # jinja's trim_blocks/lstrip_blocks already normalized the template,
        # so we do exact match first; if that fails, try lenient (collapse
        # runs of whitespace).
        if self.text.startswith(literal, self.pos):
            self.pos += len(literal)
            return
        # Lenient fallback: match literal whitespace-collapsed.
        lit_norm = re.escape(literal)
        # Replace escaped whitespace runs with \s+ (only if literal has ws)
        lit_pat = re.sub(r"(\\\s)+", r"\\s+", lit_norm)
        m = re.match(lit_pat, self.text[self.pos:])
        if m:
            self.pos += m.end()
            return
        raise InverseError(
            f"literal mismatch at pos {self.pos}: expected {literal!r}, "
            f"got {self.text[self.pos:self.pos+min(80,len(literal)+20)]!r}"
        )

    def capture_until(self, stop_literal: str | None,
                      *also_anchors: str) -> str:
        """Capture text until the EARLIEST occurrence of any anchor.
        Primary stop_literal, plus any additional fallback anchors."""
        if not stop_literal and not also_anchors:
            val = self.text[self.pos:]
            self.pos = len(self.text)
            return val
        anchors = [a for a in (stop_literal, *also_anchors) if a]
        idxs = [self.text.find(a, self.pos) for a in anchors]
        idxs = [(i, a) for i, a in zip(idxs, anchors) if i >= 0]
        if not idxs:
            raise InverseError(
                f"could not find stop literal {stop_literal!r} after pos {self.pos}"
            )
        idx, _ = min(idxs, key=lambda x: x[0])
        val = self.text[self.pos:idx]
        self.pos = idx
        return val

    # ── node dispatcher ────────────────────────────────────────────────

    def consume_nodes(self, node_list, scope: _Scope, tail_anchor: str | None = None) -> None:
        """tail_anchor: literal that follows this node_list when its own anchors
        are exhausted (e.g. for For body, the body_leading of next iteration
        or the For's own next_literal). Lets the LAST node's variable capture
        terminate cleanly."""
        i = 0
        while i < len(node_list):
            node = node_list[i]
            next_literal = self._next_literal_anchor(node_list, i + 1, scope)
            if next_literal is None:
                next_literal = tail_anchor
            # Extra fallback anchors: literals that would appear if intervening
            # If blocks were skipped. Plus the outer tail_anchor.
            extra = self._following_anchors(node_list, i + 1)
            if tail_anchor and tail_anchor not in extra:
                extra.append(tail_anchor)
            pushed = 0
            for a in extra:
                # Skip whitespace-only or too-short anchors — they cause false
                # early stops in opaque captures (JSON blobs, prose).
                if not a or not a.strip() or len(a) < 3:
                    continue
                if a != next_literal and a not in self._fallback_anchors:
                    self._fallback_anchors.append(a)
                    pushed += 1
            try:
                self.consume_node(node, scope, next_literal)
            finally:
                for _ in range(pushed):
                    self._fallback_anchors.pop()
            i += 1

    def _next_literal_anchor(self, node_list, start_idx, scope: _Scope) -> str | None:
        """Find the next literal string anchor following start_idx.
        Walks into Output's first child if it is a TemplateData."""
        for j in range(start_idx, len(node_list)):
            n = node_list[j]
            lit = self._leading_literal(n)
            if lit:
                return lit
        return None

    def _following_anchors(self, node_list, start_idx) -> list[str]:
        """Collect literal anchors at start_idx onward, treating If blocks as
        potentially-skipped: include both the If's body-leading and the literal
        that follows the If. Stops once we hit a guaranteed (non-If) literal."""
        anchors: list[str] = []
        for j in range(start_idx, len(node_list)):
            n = node_list[j]
            lit = self._leading_literal(n)
            if lit:
                anchors.append(lit)
            if isinstance(n, nodes.If):
                # If is skippable — keep walking past it to find the literal
                # that would appear if the If were absent.
                continue
            # Non-If with a leading literal is a hard stop.
            if lit:
                break
        # de-dup while preserving order
        seen = set()
        out = []
        for a in anchors:
            if a not in seen:
                seen.add(a)
                out.append(a)
        return out

    def _leading_literal(self, node) -> str | None:
        if isinstance(node, nodes.Output):
            for sub in node.nodes:
                if isinstance(sub, nodes.TemplateData):
                    if sub.data:
                        return sub.data
                return None
        if isinstance(node, nodes.For):
            for x in node.body:
                lit = self._leading_literal(x)
                if lit is not None:
                    return lit
            return None
        if isinstance(node, nodes.If):
            for x in node.body:
                lit = self._leading_literal(x)
                if lit is not None:
                    return lit
            return None
        return None

    def consume_node(self, node, scope: _Scope, next_literal: str | None) -> None:
        if isinstance(node, nodes.Output):
            self._consume_output(node, scope, next_literal)
            return
        if isinstance(node, nodes.For):
            self._consume_for(node, scope, next_literal)
            return
        if isinstance(node, nodes.If):
            self._consume_if(node, scope, next_literal)
            return
        if isinstance(node, (nodes.Assign, nodes.AssignBlock)):
            # `{% set x = ... %}` emits no output in trim-blocks/lstrip-blocks
            # mode — nothing to consume from the rendered text.
            return
        raise InverseError(f"unsupported jinja node: {type(node).__name__}")

    # ── Output (mix of TemplateData and variable expressions) ──────────

    def _consume_output(self, node: nodes.Output, scope: _Scope, next_literal: str | None) -> None:
        subs = list(node.nodes)
        for k, sub in enumerate(subs):
            # Find the next literal anchor following this sub-node:
            # either the next sub's leading literal, or next_literal if at end.
            following_lit = None
            for m in range(k + 1, len(subs)):
                nxt = subs[m]
                if isinstance(nxt, nodes.TemplateData):
                    if nxt.data:
                        following_lit = nxt.data
                    break
                # else: variable expression — no literal anchor between them.
                # Two adjacent expressions with no literal between them is
                # ambiguous; we abort to avoid silent corruption.
                if isinstance(sub, (nodes.Name, nodes.Getattr, nodes.Getitem,
                                    nodes.Filter, nodes.CondExpr, nodes.Const)):
                    raise InverseError(
                        "two adjacent expressions with no literal between them"
                    )
            if following_lit is None:
                following_lit = next_literal
            self._consume_output_sub(sub, scope, following_lit)

    def _consume_output_sub(self, sub, scope: _Scope, following_lit: str | None) -> None:
        if isinstance(sub, nodes.TemplateData):
            self.consume_literal(sub.data)
            return
        if isinstance(sub, (nodes.Name, nodes.Getattr, nodes.Getitem)):
            val = self.capture_until(following_lit, *self._fallback_anchors)
            self._assign_path(sub, scope, val)
            return
        if isinstance(sub, nodes.Filter):
            # Opaque capture: cannot reverse a filter generally. Skip-and-store
            # for traceability only.
            val = self.capture_until(following_lit, *self._fallback_anchors)
            self._opaque_n += 1
            # Try to assign to the inner Name path anyway if the filter is
            # a known pass-through like `default(x)` or `safe`.
            try:
                inner = sub.node
                if isinstance(inner, (nodes.Name, nodes.Getattr, nodes.Getitem)):
                    self._assign_path(inner, scope, val)
                    return
            except Exception:
                pass
            return
        if isinstance(sub, nodes.CondExpr):
            # `a if cond else b` — opaque capture, no assignment.
            self.capture_until(following_lit)
            return
        if isinstance(sub, nodes.Const):
            # Literal constant in template (rare); just consume its repr.
            self.consume_literal(str(sub.value))
            return
        # Generic opaque expression (Mul, Add, Sub, Concat, Compare, Test, Call,
        # Tuple, etc.) — we can't reverse it; consume up to following anchor.
        if isinstance(sub, (nodes.Mul, nodes.Add, nodes.Sub, nodes.Div, nodes.FloorDiv,
                            nodes.Mod, nodes.Pow, nodes.Concat, nodes.Compare,
                            nodes.Test, nodes.Call, nodes.Tuple, nodes.List,
                            nodes.Dict, nodes.Neg, nodes.Pos, nodes.Not)):
            self.capture_until(following_lit)
            return
        raise InverseError(f"unsupported output sub-node: {type(sub).__name__}")

    # ── For ────────────────────────────────────────────────────────────

    def _consume_for(self, node: nodes.For, scope: _Scope, next_literal: str | None) -> None:
        # Two supported forms:
        #   (a) {% for x in path %}                → list of dicts
        #   (b) {% for k, v in path.items() %}     → dict of dicts
        # Detect (b) first.
        is_items = (
            isinstance(node.target, nodes.Tuple)
            and len(node.target.items) == 2
            and all(isinstance(t, nodes.Name) for t in node.target.items)
            and isinstance(node.iter, nodes.Call)
            and isinstance(node.iter.node, nodes.Getattr)
            and node.iter.node.attr == "items"
            and not node.iter.args
        )
        if is_items:
            self._consume_for_items(node, scope, next_literal)
            return
        # Only Name/Getattr iter supported; loop.* iter not supported.
        iter_path = _path_tokens(node.iter)
        if iter_path is None:
            raise InverseError(f"unsupported For.iter: {type(node.iter).__name__}")
        # Filter expression (`for x in xs if cond`) — not reversible; we
        # treat it as ordinary loop (parse what's there).
        loop_var = node.target.name if isinstance(node.target, nodes.Name) else None
        if loop_var is None:
            raise InverseError("unsupported For.target (only single Name)")

        # We need to know what literal terminates the loop body so we can
        # decide when to stop iterating. The first TemplateData of the body
        # is what each iteration *starts* with after the first; the literal
        # *after* the loop is what terminates.
        body_leading = None
        for n in node.body:
            lit = self._leading_literal(n)
            if lit is not None:
                body_leading = lit
                break

        # Prepare list at iter_path.
        target_list = self._ensure_list_at(iter_path, scope)

        # Repeatedly try to parse one body iteration. After each, check
        # whether the next literal at self.pos starts with body_leading
        # (continue) or next_literal (stop).
        def _strip_leading_nl(s):
            return s.lstrip("\n") if s else s

        while True:
            # Decide whether to keep iterating.
            if body_leading is not None and next_literal is not None:
                # Prefer next_literal (loop exit) over body_leading when both
                # could match — check stronger signals first.
                nl_stripped = _strip_leading_nl(next_literal)
                # Strongest: full next_literal matches verbatim.
                if self.text.startswith(next_literal, self.pos):
                    break
                # If body_leading is a prefix of next_literal (ambiguous), use
                # a longer test: does the FULL next_literal (sans leading \n)
                # match? If so, exit loop.
                if (nl_stripped and
                    not body_leading.startswith(nl_stripped) and
                    self.text.startswith(nl_stripped, self.pos)):
                    break
                if not self.text.startswith(body_leading, self.pos):
                    # Neither matches — could be whitespace difference.
                    skipped = self.pos
                    while skipped < len(self.text) and self.text[skipped] in " \t":
                        skipped += 1
                    if self.text.startswith(next_literal, skipped):
                        self.pos = skipped
                        break
                    if not self.text.startswith(body_leading, skipped):
                        break
            elif next_literal is not None:
                if self.text.startswith(next_literal, self.pos):
                    break
            elif body_leading is not None:
                if not self.text.startswith(body_leading, self.pos):
                    break
            else:
                # No anchors at all — parse exactly one iteration.
                pass

            # Parse one iteration.
            _pos_before = self.pos
            item: dict = {}
            scope.binds[loop_var] = item
            tail = body_leading or next_literal
            # Push next_literal as fallback anchor so the LAST field's capture
            # stops at the loop exit if it would otherwise sail past it.
            pushed = False
            if (next_literal and next_literal != tail
                    and next_literal.strip() and len(next_literal) >= 3):
                self._fallback_anchors.append(next_literal)
                pushed = True
            try:
                self.consume_nodes(node.body, scope, tail_anchor=tail)
            finally:
                scope.binds.pop(loop_var, None)
                if pushed:
                    self._fallback_anchors.pop()
            target_list.append(item)

            if next_literal is None and body_leading is None:
                break
            if self.pos == _pos_before:
                # Zero-progress iteration (body only Assign/no visible output)
                # — would loop forever; bail out.
                break

        # Rewind by 1 char if next_literal would match with a leading newline
        # that we already consumed as the body's trailing newline. (jinja
        # trim_blocks collapses successive body trailing-newlines into the
        # next block's leading newline.)
        if next_literal and not self.text.startswith(next_literal, self.pos):
            if next_literal.startswith("\n") and self.pos > 0 and self.text[self.pos - 1] == "\n":
                if self.text.startswith(next_literal[1:], self.pos):
                    self.pos -= 1

    def _consume_for_items(self, node: nodes.For, scope: _Scope, next_literal: str | None) -> None:
        """Handle `{% for k, v in dict_path.items() %}` — dict-of-dict."""
        k_var = node.target.items[0].name
        v_var = node.target.items[1].name

        # Resolve the dict path. iter is Call(Getattr(<dict_expr>, 'items'), []).
        dict_expr = node.iter.node.node
        # Unwrap `(x or {})` → x
        if isinstance(dict_expr, nodes.Or) and isinstance(dict_expr.right, nodes.Dict) and not dict_expr.right.items:
            dict_expr = dict_expr.left
        iter_path = _path_tokens(dict_expr)
        if iter_path is None:
            raise InverseError(
                f"unsupported items() dict path: {type(dict_expr).__name__}"
            )

        # Determine body_leading literal (first iteration body text).
        body_leading = None
        for n in node.body:
            lit = self._leading_literal(n)
            if lit is not None:
                body_leading = lit
                break

        target_dict = self._ensure_dict_at(iter_path, scope)

        def _strip_leading_nl(s):
            return s.lstrip("\n") if s else s

        while True:
            # Loop-exit decision (mirrors _consume_for).
            if body_leading is not None and next_literal is not None:
                nl_stripped = _strip_leading_nl(next_literal)
                if self.text.startswith(next_literal, self.pos):
                    break
                if (nl_stripped and
                    not body_leading.startswith(nl_stripped) and
                    self.text.startswith(nl_stripped, self.pos)):
                    break
                if not self.text.startswith(body_leading, self.pos):
                    skipped = self.pos
                    while skipped < len(self.text) and self.text[skipped] in " \t":
                        skipped += 1
                    if self.text.startswith(next_literal, skipped):
                        self.pos = skipped
                        break
                    if not self.text.startswith(body_leading, skipped):
                        break
            elif next_literal is not None:
                if self.text.startswith(next_literal, self.pos):
                    break
            elif body_leading is not None:
                if not self.text.startswith(body_leading, self.pos):
                    break
            else:
                pass

            _pos_before = self.pos
            k_holder: dict = {}
            v_item: dict = {}
            scope.binds[k_var] = k_holder
            scope.binds[v_var] = v_item
            tail = body_leading or next_literal
            pushed = False
            if (next_literal and next_literal != tail
                    and next_literal.strip() and len(next_literal) >= 3):
                self._fallback_anchors.append(next_literal)
                pushed = True
            try:
                self.consume_nodes(node.body, scope, tail_anchor=tail)
            finally:
                scope.binds.pop(k_var, None)
                scope.binds.pop(v_var, None)
                if pushed:
                    self._fallback_anchors.pop()

            key_value = k_holder.get("_value")
            if key_value is None:
                # Couldn't capture the key — fall back to positional index so
                # we don't lose the value, but signal this is unusual.
                key_value = f"_unkeyed_{len(target_dict)}"
            target_dict[str(key_value)] = v_item

            if next_literal is None and body_leading is None:
                break
            if self.pos == _pos_before:
                break

        if next_literal and not self.text.startswith(next_literal, self.pos):
            if next_literal.startswith("\n") and self.pos > 0 and self.text[self.pos - 1] == "\n":
                if self.text.startswith(next_literal[1:], self.pos):
                    self.pos -= 1

    def _ensure_dict_at(self, tokens: list[str], scope: _Scope) -> dict:
        if tokens and tokens[0] in scope.binds:
            target = scope.binds[tokens[0]]
            rest = tokens[1:]
            if not rest:
                raise InverseError("can't iterate items() over the loop variable itself")
            return _nested_get_or_create_dict(target, rest)
        return _nested_get_or_create_dict(self.data, tokens)

    # ── If ─────────────────────────────────────────────────────────────

    def _consume_if(self, node: nodes.If, scope: _Scope, next_literal: str | None) -> None:
        # Try the "true" branch by peeking at its leading literal.
        true_leading = None
        for n in node.body:
            lit = self._leading_literal(n)
            if lit is not None:
                true_leading = lit
                break
        else_branch = node.else_ or []
        false_leading = None
        for n in else_branch:
            lit = self._leading_literal(n)
            if lit is not None:
                false_leading = lit
                break

        # Decision logic:
        # - If true_leading matches at pos → take true branch.
        # - Else if false_leading matches → take else branch.
        # - Else if true branch has no leading literal (pure capture) →
        #   we cannot tell; default to skip (safer; many `{% if x %}` blocks
        #   in genecr templates are optional fields).
        take_true = False
        if true_leading and self.text.startswith(true_leading, self.pos):
            take_true = True
        elif false_leading and self.text.startswith(false_leading, self.pos):
            take_true = False
        elif next_literal and self.text.startswith(next_literal, self.pos):
            take_true = False
        else:
            # No way to decide — default skip.
            take_true = False

        # If both branches share an ambiguous leading literal AND we have an
        # else branch, try the true branch first; if the subsequent
        # next_literal anchor doesn't appear at the new pos, backtrack and try
        # the else branch.
        ambiguous = (true_leading and false_leading and true_leading == false_leading)
        if take_true:
            if ambiguous and else_branch:
                # Check post-condition: any of next_literal or fallback anchors
                # should match at new pos after the chosen branch.
                check_anchors = [a for a in (next_literal, *self._fallback_anchors) if a]
                saved_pos = self.pos
                saved_data = _snapshot(self.data)
                ok = False
                try:
                    self.consume_nodes(node.body, scope, tail_anchor=next_literal)
                    ok = (not check_anchors) or any(
                        self.text.startswith(a, self.pos) for a in check_anchors
                    )
                except InverseError:
                    ok = False
                if not ok:
                    self.pos = saved_pos
                    _restore(self.data, saved_data)
                    self.consume_nodes(else_branch, scope, tail_anchor=next_literal)
            else:
                self.consume_nodes(node.body, scope, tail_anchor=next_literal)
        elif else_branch:
            self.consume_nodes(else_branch, scope, tail_anchor=next_literal)
        # else: skip both — field stays unset.

    # ── path resolution / assignment ───────────────────────────────────

    def _assign_path(self, expr, scope: _Scope, value: str) -> None:
        tokens = _path_tokens(expr)
        if tokens is None:
            return  # unsupported path — ignore silently
        # Skip read-only loop vars (loop.index, loop.last, etc.)
        if tokens and tokens[0] == "loop":
            return
        # If first token is a loop-bound variable, write into that item dict.
        if tokens and tokens[0] in scope.binds:
            target = scope.binds[tokens[0]]
            rest = tokens[1:]
            if not rest:
                # `{{ x }}` where x is the loop var itself (e.g. for s in scenarios → {{ s }})
                # We can't really represent that; store under "_value".
                target["_value"] = value
                return
            _nested_set(target, rest, value)
            return
        # Otherwise write to top-level data.
        _nested_set(self.data, tokens, value)

    def _ensure_list_at(self, tokens: list[str], scope: _Scope) -> list:
        if tokens and tokens[0] in scope.binds:
            target = scope.binds[tokens[0]]
            rest = tokens[1:]
            if not rest:
                raise InverseError("can't iterate over the loop variable itself")
            return _nested_get_or_create_list(target, rest)
        return _nested_get_or_create_list(self.data, tokens)


# ─── path helpers ───────────────────────────────────────────────────────


def _path_tokens(node) -> list[str] | None:
    """Convert Name/Getattr/Getitem chain into list of string tokens."""
    if isinstance(node, nodes.Name):
        return [node.name]
    if isinstance(node, nodes.Getattr):
        inner = _path_tokens(node.node)
        if inner is None:
            return None
        return inner + [node.attr]
    if isinstance(node, nodes.Getitem):
        inner = _path_tokens(node.node)
        if inner is None:
            return None
        arg = node.arg
        key = arg.value if hasattr(arg, "value") else None
        if key is None:
            return None
        return inner + [str(key)]
    return None


def _nested_set(d: dict, tokens: list[str], value: Any) -> None:
    cur = d
    for t in tokens[:-1]:
        if t not in cur or not isinstance(cur[t], dict):
            cur[t] = {}
        cur = cur[t]
    cur[tokens[-1]] = value


def _nested_get_or_create_dict(d: dict, tokens: list[str]) -> dict:
    cur = d
    for t in tokens[:-1]:
        if t not in cur or not isinstance(cur[t], dict):
            cur[t] = {}
        cur = cur[t]
    last = tokens[-1]
    if last not in cur or not isinstance(cur[last], dict):
        cur[last] = {}
    return cur[last]


def _nested_get_or_create_list(d: dict, tokens: list[str]) -> list:
    cur = d
    for t in tokens[:-1]:
        if t not in cur or not isinstance(cur[t], dict):
            cur[t] = {}
        cur = cur[t]
    last = tokens[-1]
    if last not in cur or not isinstance(cur[last], list):
        cur[last] = []
    return cur[last]
