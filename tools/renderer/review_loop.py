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
    max_rounds: int = 3,
) -> RunStepResult:
    """Program-controlled loop. Three independent AI subagents.

    Flow:
      1. Generator produces initial input.json
      2. For up to max_rounds:
         a. Schema validate (program)
         b. cross_check (program)
         c. Reviewer subagent (independent)
         d. If all issue lists empty → success
         e. Else: fixer subagent (independent) → new input.json
    """
    # 1. Generator
    gen_raw = ai_invoker("generator", {
        "step": step_name,
        "upstream": all_data,
    })
    try:
        data = _parse_json(gen_raw)
    except Exception as e:
        return RunStepResult(
            success=False, attempts=0,
            final_issues=[Issue(step=step_name, category="generator_invalid_json",
                                detail=str(e))],
        )

    last_issues: list[Issue] = []

    for attempt in range(1, max_rounds + 1):
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

        # Fixer (independent subagent) — only if we have more rounds left
        if attempt >= max_rounds:
            break

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

    return RunStepResult(
        success=False, attempts=max_rounds, data=data,
        final_issues=last_issues,
    )
