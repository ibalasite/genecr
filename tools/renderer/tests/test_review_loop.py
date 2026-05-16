"""Tests for program-orchestrated generate → schema/cross_check → review → fix loop.

Three AI roles (generator / reviewer / fixer) are independent invocations.
Same AI never reviews or fixes its own output — pipeline owns the flow.
Tests mock the AI invoker to verify call sequencing & convergence.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from cross_check import Issue
from review_loop import RunStepResult, run_step


@dataclass
class FakeAI:
    """Records every (role, payload) invocation; returns scripted outputs.

    Each role's response queue is consumed FIFO. Test asserts the number of
    invocations per role to prove three INDEPENDENT calls happened.
    """
    responses: dict[str, list[str]] = field(default_factory=dict)
    log: list[tuple[str, dict]] = field(default_factory=list)

    def __call__(self, role: str, payload: dict) -> str:
        self.log.append((role, payload))
        queue = self.responses.get(role, [])
        if not queue:
            raise AssertionError(f"FakeAI: no scripted response for role={role}")
        return queue.pop(0)

    def count(self, role: str) -> int:
        return sum(1 for r, _ in self.log if r == role)


# ─── helpers ────────────────────────────────────────────────────────────────

def _ok_schema(input_data):
    return []  # no errors


def _fail_schema_once_then_ok():
    calls = {"n": 0}
    def fn(input_data):
        calls["n"] += 1
        if calls["n"] == 1:
            return ["root.feature: missing 'name'"]
        return []
    return fn


def _ok_cross_check(step_name, all_data):
    return []


def _fail_cross_check_then_ok():
    calls = {"n": 0}
    def fn(step_name, all_data):
        calls["n"] += 1
        if calls["n"] == 1:
            return [Issue(step=step_name, category="x", detail="count off")]
        return []
    return fn


# ─── happy path ─────────────────────────────────────────────────────────────

def test_happy_path_one_round():
    """Generator produces valid output; schema passes; cross_check empty;
    reviewer returns no issues. Should finish after exactly 1 generator + 1
    reviewer call, ZERO fixer calls."""
    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "reviewer":  [json.dumps({"issues": []})],
    })
    result = run_step(
        step_name="spec-basic",
        all_data={},
        ai_invoker=ai,
        schema_validate=_ok_schema,
        cross_check_fn=_ok_cross_check,
    )
    assert result.success
    assert ai.count("generator") == 1
    assert ai.count("reviewer") == 1
    assert ai.count("fixer") == 0
    assert result.attempts == 1


# ─── reviewer surfaces issues → fixer runs ──────────────────────────────────

def test_reviewer_finds_issues_fixer_corrects():
    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "reviewer":  [
            json.dumps({"issues": [
                {"category": "weak", "detail": "competitor too shallow"}
            ]}),
            json.dumps({"issues": []}),
        ],
        "fixer":     [json.dumps({"feature": {"name": "x2", "slug": "x"}})],
    })
    result = run_step("spec-basic", {}, ai, _ok_schema, _ok_cross_check)
    assert result.success
    assert ai.count("generator") == 1
    assert ai.count("reviewer") == 2  # initial review + post-fix re-review
    assert ai.count("fixer") == 1


# ─── schema failure routes to fixer (not generator) ─────────────────────────

def test_schema_failure_invokes_fixer_not_regenerate():
    """Schema error must go to fixer subagent (independent), not loop back
    to generator. The generator output is mutated by the fixer."""
    ai = FakeAI(responses={
        "generator": [json.dumps({"bad": True})],
        "fixer":     [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "reviewer":  [json.dumps({"issues": []})],
    })
    result = run_step(
        "spec-basic", {}, ai,
        schema_validate=_fail_schema_once_then_ok(),
        cross_check_fn=_ok_cross_check,
    )
    assert result.success
    assert ai.count("generator") == 1
    assert ai.count("fixer") == 1
    assert ai.count("reviewer") == 1


# ─── cross_check failure feeds fixer ────────────────────────────────────────

def test_cross_check_failure_feeds_fixer():
    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "fixer":     [json.dumps({"feature": {"name": "x2", "slug": "x"}})],
        "reviewer":  [json.dumps({"issues": []})],
    })
    result = run_step(
        "assets", {"assets": {}}, ai,
        schema_validate=_ok_schema,
        cross_check_fn=_fail_cross_check_then_ok(),
    )
    assert result.success
    assert ai.count("fixer") == 1


# ─── max rounds exceeded → step-fail ────────────────────────────────────────

def test_max_rounds_exceeded_returns_failure():
    """Reviewer never converges → after max_rounds, return failure with
    remaining issues — DO NOT silently mark done."""
    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "fixer":     [json.dumps({"feature": {"name": "x", "slug": "x"}})] * 5,
        "reviewer":  [json.dumps({"issues": [{"category": "c", "detail": "still bad"}]})] * 10,
    })
    result = run_step(
        "spec-basic", {}, ai,
        schema_validate=_ok_schema,
        cross_check_fn=_ok_cross_check,
        max_rounds=2,
    )
    assert not result.success
    assert result.attempts == 2
    assert len(result.final_issues) >= 1


# ─── independence guarantee ─────────────────────────────────────────────────

def test_three_roles_receive_independent_payloads():
    """Reviewer payload must NOT include generator's thought process —
    only the current input data + role-specific context.
    Fixer payload must include the issues list."""
    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "reviewer":  [json.dumps({"issues": [{"category": "c", "detail": "d"}]}),
                      json.dumps({"issues": []})],
        "fixer":     [json.dumps({"feature": {"name": "y", "slug": "x"}})],
    })
    run_step("spec-basic", {}, ai, _ok_schema, _ok_cross_check)

    roles_seen = [r for r, _ in ai.log]
    # Sequence: generator → reviewer → fixer → reviewer
    assert roles_seen == ["generator", "reviewer", "fixer", "reviewer"]

    # Reviewer payload should contain the current input but NOT a 'previous_thoughts' field
    _, rev_payload = ai.log[1]
    assert "input" in rev_payload
    assert "previous_thoughts" not in rev_payload  # explicit independence

    # Fixer payload must include issues to fix
    _, fix_payload = ai.log[2]
    assert "issues" in fix_payload
    assert len(fix_payload["issues"]) == 1


def test_step_name_passed_to_cross_check():
    """cross_check needs to know which step to route issues to."""
    captured = {}
    def spy(step_name, all_data):
        captured["step_name"] = step_name
        return []

    ai = FakeAI(responses={
        "generator": [json.dumps({"feature": {"name": "x", "slug": "x"}})],
        "reviewer":  [json.dumps({"issues": []})],
    })
    run_step("bdd", {}, ai, _ok_schema, spy)
    assert captured["step_name"] == "bdd"


# ─── result data is the final accepted input.json ───────────────────────────

def test_result_includes_final_data():
    final_data = {"feature": {"name": "final", "slug": "x"}}
    ai = FakeAI(responses={
        "generator": [json.dumps(final_data)],
        "reviewer":  [json.dumps({"issues": []})],
    })
    result = run_step("spec-basic", {}, ai, _ok_schema, _ok_cross_check)
    assert result.success
    assert result.data == final_data
