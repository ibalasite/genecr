"""Prompts must wire upstream outputs per the dependency chain.

Downstream steps that ignore upstream produce contradictions (e.g. spec
says 20 images, assets lists 10). Pipeline substitutes {step_content}
placeholders; this test verifies each prompt requests its upstream inputs.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS = REPO_ROOT / "templates" / "prompts"

# Dependency chain (confirmed with user).
UPSTREAM = {
    "spec-basic":    [],
    "spec-advanced": ["spec_basic"],
    "assets":        ["spec_basic"],
    "bdd":           ["spec_basic", "spec_advanced", "assets"],
    "scrum":         ["spec_basic", "spec_advanced", "assets"],
    "prototype":     ["spec_basic", "spec_advanced", "assets"],
    "docs":          ["spec_basic", "spec_advanced", "assets",
                      "bdd", "scrum", "prototype"],
}


@pytest.mark.parametrize("step,upstream_steps", list(UPSTREAM.items()))
def test_prompt_references_each_upstream(step, upstream_steps):
    body = (PROMPTS / f"{step}.prompt.md").read_text(encoding="utf-8")
    for u in upstream_steps:
        placeholder = "{" + u + "_content}"
        assert placeholder in body, (
            f"{step}.prompt.md missing upstream placeholder {placeholder}"
        )


def test_spec_basic_requires_resource_counts():
    body = (PROMPTS / "spec-basic.prompt.md").read_text(encoding="utf-8")
    assert "resource_counts" in body
    assert "RESOURCE COUNTS" in body or "resource counts" in body.lower()


def test_spec_advanced_requires_db_queries_and_redis_ops():
    body = (PROMPTS / "spec-advanced.prompt.md").read_text(encoding="utf-8")
    assert "db_queries" in body
    assert "redis_ops" in body
    assert "create_table_sql" in body
    assert "redis_pattern" in body


def test_bdd_emphasizes_sequence_diagram():
    body = (PROMPTS / "bdd.prompt.md").read_text(encoding="utf-8")
    assert "sequence_diagram" in body
    assert "sequenceDiagram" in body


def test_assets_aligns_with_spec_basic_resource_counts():
    body = (PROMPTS / "assets.prompt.md").read_text(encoding="utf-8")
    assert "resource_counts" in body
    assert "cross_check" in body.lower() or "mechanically" in body.lower()


# ── generator strengthening (convergence triangle: gen quality first hit) ──

GENERATOR_STEPS = ["spec-basic", "spec-advanced", "assets", "bdd",
                   "scrum", "prototype", "docs"]


@pytest.mark.parametrize("step", GENERATOR_STEPS)
def test_prompt_has_stakes_block(step):
    body = (PROMPTS / f"{step}.prompt.md").read_text(encoding="utf-8")
    assert "## STAKES" in body, f"{step} missing STAKES block"


@pytest.mark.parametrize("step", GENERATOR_STEPS)
def test_prompt_has_preflight_checklist(step):
    body = (PROMPTS / f"{step}.prompt.md").read_text(encoding="utf-8")
    assert "PRE-FLIGHT CHECKLIST" in body, f"{step} missing PRE-FLIGHT block"
    # Pre-flight should reference at least the first 3 review rules
    for tag in ("R1", "R2", "R3"):
        assert f"- {tag}" in body, f"{step} pre-flight missing {tag}"


@pytest.mark.parametrize("step", GENERATOR_STEPS)
def test_prompt_has_output_language_directive(step):
    body = (PROMPTS / f"{step}.prompt.md").read_text(encoding="utf-8")
    assert "OUTPUT LANGUAGE" in body, f"{step} missing OUTPUT LANGUAGE block"
    assert "Traditional Chinese" in body or "zh-TW" in body
    assert "string field" in body.lower() or "field values" in body.lower()


def test_bdd_preflight_flags_sequence_diagram_required():
    body = (PROMPTS / "bdd.prompt.md").read_text(encoding="utf-8")
    assert "sequence_diagram" in body.lower()
    # User-flagged critical phrase explicitly present
    assert "user-flagged critical" in body.lower() or "critical" in body.lower()
