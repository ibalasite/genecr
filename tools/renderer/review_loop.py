"""Program-orchestrated generate → review → fix loop.

Pipeline owns the flow; AI does single-purpose tasks per invocation.
Three roles (generator / reviewer / fixer) are INDEPENDENT subagents:
each receives only its task-specific payload, never the prior agent's
thoughts or scratchpad. This avoids the self-affirmation bias of a
single AI reviewing its own output.

ai_invoker(role, payload) -> str returns the AI's raw output. The caller
(pipeline) wires this to a real subprocess call; tests mock it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable

from cross_check import Issue

AIInvoker = Callable[[str, dict], str]
SchemaValidator = Callable[[dict], list[str]]          # data -> error strings
CrossCheckFn = Callable[[str, dict], list[Issue]]       # step, all_data -> issues


@dataclass
class RunStepResult:
    success: bool
    attempts: int
    data: dict | None = None
    final_issues: list[Issue] = field(default_factory=list)


def _parse_json(raw: str) -> dict:
    """Tolerate AI wrapping JSON in fenced blocks or stray prose."""
    raw = (raw or "").strip()
    if raw.startswith("```"):
        # strip first fence line and trailing fence
        lines = raw.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        while lines and not lines[-1].strip().startswith("```") is False and lines[-1].strip() == "```":
            lines = lines[:-1]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return json.loads(raw)


def _ensure_valid_json(initial_raw: str,
                        gen_fixer_invoker: Callable[[str, str], str]) -> dict:
    """Type-level loop：把 raw 收斂成合法 JSON dict（無 iter cap）。

    每輪：① 程式 parse → ② 程式 json_repair → ③ AI gen_fixer（窄 prompt）。
    任一步 OK 就 return。

    收斂理論：gen_fixer prompt 寫死「只動格式不動內容」，每輪只可能變更好或不變；
    剎車條件 = AI 兩次輸出完全相同（卡在同輸出無進展時 break，避免無限呼叫）。
    """
    raw = initial_raw
    last_err: Exception | None = None
    iteration = 0
    same_count = 0  # AI 回同樣輸出累計次數；達 3 次認輸（給 AI 兩次隨機性機會）
    while True:
        iteration += 1
        # tier 1: 程式直接 parse（含 fenced-block 容忍）
        try:
            return _parse_json(raw)
        except Exception as e:
            last_err = e
        # tier 2: 程式 json_repair（無 AI cost，補逗號/括號/單引號/全形/註解等）
        try:
            from json_repair import repair_json
            repaired = repair_json(raw)
            return json.loads(repaired)
        except Exception:
            pass
        # tier 3: AI gen_fixer 窄 prompt（只看 raw 末段 + parse error，省 token）
        new_raw = gen_fixer_invoker(_trim_for_fixer(raw), str(last_err))
        # 剎車：AI 沒回 / 連續 3 次回同樣的東西 → break 避免無限呼叫
        if not new_raw or new_raw == raw:
            same_count += 1
            if same_count >= 3:
                raise ValueError(
                    f"type-level convergence stalled at iter {iteration}: "
                    f"AI fixer produced same output 3 times in a row. Last error: {last_err}"
                )
        else:
            same_count = 0  # AI 出新東西，重置計數
            raw = new_raw


def _trim_for_fixer(raw: str, max_chars: int = 4000) -> str:
    """Gen_fixer 不需要看整段 raw（可能 30K+ 字），只需要錯誤附近的局部。
    保留前 1000 字（看開頭格式）+ 末 3000 字（錯誤通常在末段附近）。"""
    if len(raw) <= max_chars:
        return raw
    head_n = 1000
    tail_n = max_chars - head_n
    return raw[:head_n] + "\n\n... [TRUNCATED FOR FIXER, original total " \
        + str(len(raw)) + " chars] ...\n\n" + raw[-tail_n:]


def _parse_review_issues(raw: str, step_name: str) -> list[Issue]:
    """Reviewer response shape: {"issues": [{"category": ..., "detail": ...}, ...]}"""
    try:
        obj = _parse_json(raw)
    except Exception:
        return []
    issues = []
    for it in obj.get("issues", []):
        issues.append(Issue(
            step=step_name,
            category=it.get("category", "reviewer"),
            detail=it.get("detail", ""),
        ))
    return issues


def run_step(
    step_name: str,
    all_data: dict,
    ai_invoker: AIInvoker,
    schema_validate: SchemaValidator,
    cross_check_fn: CrossCheckFn,
    max_rounds: int | None = None,
    initial_data: dict | None = None,
) -> RunStepResult:
    """Program-controlled loop. Three independent AI subagents.

    The ONLY success criterion is `len(all_issues) == 0` (program-counted,
    not AI-self-reported). There is NO N-round 'give up' threshold —
    arbitrary numbers (3, 20, ...) violate the finding=0 principle.

    `max_rounds=None` (default) = no cap; loop until convergence or human
    aborts. User may pass a small integer in tests to keep test runs cheap;
    production runs leave it None.

    Flow:
      1. Generator produces initial input.json
      2. Loop:
         a. Schema validate (program)
         b. cross_check (program)
         c. Reviewer subagent (independent)
         d. If all issue lists empty → SUCCESS
         e. Else: fixer subagent (independent) → new input.json
    """
    # 1. Generator — skipped when initial_data is provided (revalidate mode:
    # an existing <step>.input.json is fed in directly so we re-check it
    # against current rules without burning tokens on regeneration).
    if initial_data is not None:
        data = initial_data
    else:
        gen_raw = ai_invoker("generator", {
            "step": step_name,
            "upstream": all_data,
        })
        # Type-level loop：gen → check → program fix → check → AI gen_fixer → check → loop
        # 收斂前提：每輪只動格式不動內容；max_iter 防發散。
        try:
            data = _ensure_valid_json(
                gen_raw,
                gen_fixer_invoker=lambda raw, err: ai_invoker("gen_fixer", {
                    "step": step_name, "raw": raw, "parse_error": err,
                }),
            )
        except ValueError as e:
            return RunStepResult(
                success=False, attempts=0,
                final_issues=[Issue(step=step_name, category="generator_invalid_json",
                                    detail=str(e))],
            )

    last_issues: list[Issue] = []
    attempt = 0
    while max_rounds is None or attempt < max_rounds:
        attempt += 1
        # Update all_data so cross_check sees the current step's output
        all_data = {**all_data, step_name: data}

        # Program checks first (cheap, no AI cost).
        schema_errs = schema_validate(data)
        schema_issues = [
            Issue(step=step_name, category="schema_error", detail=err)
            for err in schema_errs
        ]
        cross_issues = cross_check_fn(step_name, all_data)
        program_issues = schema_issues + cross_issues

        if program_issues:
            # Skip reviewer this round — fixer first repairs format/alignment.
            review_issues = []
        else:
            # Format/alignment clean → reviewer subagent does semantic review.
            rev_raw = ai_invoker("reviewer", {
                "step": step_name,
                "input": data,
                "upstream": {k: v for k, v in all_data.items() if k != step_name},
            })
            review_issues = _parse_review_issues(rev_raw, step_name)

        all_issues = program_issues + review_issues
        last_issues = all_issues

        if not all_issues:
            return RunStepResult(success=True, attempts=attempt, data=data)

        # Fixer (independent subagent) — no early exit; only end is finding=0
        fix_raw = ai_invoker("fixer", {
            "step": step_name,
            "input": data,
            "issues": [i.to_dict() for i in all_issues],
            "upstream": {k: v for k, v in all_data.items() if k != step_name},
        })
        try:
            data = _parse_json(fix_raw)
        except Exception as e:
            return RunStepResult(
                success=False, attempts=attempt,
                data=data,
                final_issues=last_issues + [Issue(
                    step=step_name, category="fixer_invalid_json", detail=str(e),
                )],
            )

    # Only reachable when max_rounds is set (tests). Production = loop forever
    # until finding=0 or exception.
    return RunStepResult(
        success=False, attempts=attempt, data=data,
        final_issues=last_issues,
    )
