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


def _is_truncated(raw: str) -> bool:
    """截斷判斷：開頭是 { 但 parse 失敗，代表 AI 生成到一半被 token limit 截斷。"""
    stripped = raw.strip()
    if not stripped.startswith('{'):
        return False
    try:
        json.loads(stripped)
        return False
    except json.JSONDecodeError:
        return True


def _ensure_valid_json(initial_raw: str,
                        gen_fixer_invoker: Callable[[str, str], str],
                        tail_completer_invoker: Callable[[str, list[str]], str] | None = None,
                        required_keys: list[str] | None = None) -> dict:
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
        # 必須是 dict — 若 AI 寫成 list / scalar 視為 type error 進下一輪
        try:
            result = _parse_json(raw)
            if isinstance(result, dict):
                return result
            last_err = TypeError(
                f"expected JSON object (dict), got {type(result).__name__}"
            )
        except Exception as e:
            last_err = e
        # tier 1.5: 截斷補完（只在第一輪、有 tail_completer、且確認是截斷時觸發）
        # 必須在 json_repair 之前，否則 json_repair 把截斷 JSON「勉強補完」，
        # 丟失後半段內容；截斷補完保留 90%+ 並只請 AI 補缺失尾巴。
        if iteration == 1 and tail_completer_invoker is not None and _is_truncated(raw):
            missing = []
            if required_keys:
                missing = [k for k in required_keys if f'"{k}"' not in raw]
            tail_raw = tail_completer_invoker(raw, missing)
            if tail_raw and tail_raw.strip():
                combined = raw.rstrip() + "\n" + tail_raw.lstrip()
                try:
                    result = _parse_json(combined)
                    if isinstance(result, dict):
                        return result
                except Exception:
                    pass
                try:
                    from json_repair import repair_json
                    parsed = json.loads(repair_json(combined))
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
                # 補完後仍失敗，把 combined 當新 raw 繼續走後面 tier
                raw = combined

        # tier 2: 程式 json_repair（無 AI cost，補逗號/括號/單引號/全形/註解等）
        # 同樣要求 dict — json_repair 有時會把「多 dict 連著」修成 list，
        # 那也不接受，繼續下一輪讓 AI gen_fixer 重新生成 dict。
        try:
            from json_repair import repair_json
            repaired = repair_json(raw)
            parsed = json.loads(repaired)
            if isinstance(parsed, dict):
                return parsed
            last_err = TypeError(
                f"json_repair produced {type(parsed).__name__}, expected dict"
            )
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


_OUTPUT_TOO_SMALL_RATIO = 0.10  # generator output < 10% of prompt → 視為無效，要求重建


def run_step(
    step_name: str,
    all_data: dict,
    ai_invoker: AIInvoker,
    schema_validate: SchemaValidator,
    cross_check_fn: CrossCheckFn,
    max_rounds: int | None = None,
    initial_data: dict | None = None,
    schema_required_keys: list[str] | None = None,
    work_dir: "Path | None" = None,
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
    _generator_too_small: Issue | None = None  # 帶進第一輪 program_issues

    if initial_data is not None:
        data = initial_data
    else:
        # Layer 1：generator output 太小 → 在 gen loop 直接重打，不讓壞 data 往下
        _GEN_RETRIES = 2
        for _gen_attempt in range(1 + _GEN_RETRIES):
            gen_raw = ai_invoker("generator", {
                "step": step_name,
                "upstream": all_data,
            })
            _prompt_size = 0
            if work_dir is not None:
                from pathlib import Path as _Path
                _pf = _Path(work_dir) / f"{step_name}.generator.combined.prompt.md"
                if _pf.exists():
                    _prompt_size = _pf.stat().st_size
            _output_size = len(gen_raw.encode("utf-8"))
            _ratio = _output_size / _prompt_size if _prompt_size > 0 else 1.0
            print(f"   [size check] gen attempt {_gen_attempt+1}: output {_output_size:,} B"
                  f" / prompt {_prompt_size:,} B = {_ratio:.1%}")
            if _ratio >= _OUTPUT_TOO_SMALL_RATIO:
                break  # 正常，往下走
            if _gen_attempt < _GEN_RETRIES:
                print(f"   [size check] ⚠ too small — retrying generator ({_gen_attempt+1}/{_GEN_RETRIES})")
            else:
                # Layer 2 safety net：全部重試仍太小，標記讓 fixer 知道要重建
                print(f"   [size check] ❌ still too small after {_GEN_RETRIES} retries — escalating to fixer")
                _generator_too_small = Issue(
                    step=step_name,
                    category="output_too_small",
                    detail=(
                        f"generator {_gen_attempt+1} 次輸出皆 < {_OUTPUT_TOO_SMALL_RATIO:.0%} of prompt"
                        f"（最後一次 {_output_size:,} / {_prompt_size:,} = {_ratio:.1%}）"
                        f"，fixer 請從頭完整重建"
                    ),
                )

        # Type-level loop：gen → check → program fix → check → AI gen_fixer → check → loop
        try:
            data = _ensure_valid_json(
                gen_raw,
                gen_fixer_invoker=lambda raw, err: ai_invoker("gen_fixer", {
                    "step": step_name, "raw": raw, "parse_error": err,
                }),
                tail_completer_invoker=lambda raw, missing: ai_invoker("tail_completer", {
                    "step": step_name, "truncated_raw": raw, "missing_keys": missing,
                }),
                required_keys=schema_required_keys,
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

        # 第一輪注入 output_too_small（若有），之後清除
        extra_program: list[Issue] = []
        if attempt == 1 and _generator_too_small is not None:
            extra_program = [_generator_too_small]
            _generator_too_small = None  # 只注入一次

        # Program checks first (cheap, no AI cost).
        schema_errs = schema_validate(data)
        schema_issues = [
            Issue(step=step_name, category="schema_error", detail=err)
            for err in schema_errs
        ]
        # cross_check 只在 schema 乾淨時才跑，確保 cross_check
        # 不會因為欄位型別錯誤（如 responses 是 list）而 crash。
        if schema_issues:
            cross_issues = []
        else:
            cross_issues = cross_check_fn(step_name, all_data)
        program_issues = extra_program + schema_issues + cross_issues

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
