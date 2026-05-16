"""Reviewer/fixer prompt templates exist and have step-specific rules per step."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS = REPO_ROOT / "templates" / "prompts"
REVIEW = REPO_ROOT / "templates" / "review"

ALL_STEPS = [
    "spec-basic", "spec-advanced", "assets",
    "bdd", "scrum", "prototype", "docs",
]


def test_reviewer_skeleton_exists():
    p = PROMPTS / "_review.prompt.md"
    assert p.exists()
    body = p.read_text(encoding="utf-8")
    assert "INDEPENDENT REVIEWER" in body
    assert "{step_review_rules}" in body
    assert "{input_data}" in body
    assert "{upstream_outputs}" in body


def test_fixer_skeleton_exists():
    p = PROMPTS / "_fixer.prompt.md"
    assert p.exists()
    body = p.read_text(encoding="utf-8")
    assert "INDEPENDENT FIXER" in body
    assert "{issues}" in body
    assert "{input_data}" in body
    assert "{upstream_outputs}" in body


@pytest.mark.parametrize("step", ALL_STEPS)
def test_step_review_rules_exist(step):
    p = REVIEW / f"{step}.review.md"
    assert p.exists(), f"missing {p}"
    body = p.read_text(encoding="utf-8")
    assert len(body) > 200, f"{step}.review.md too short ({len(body)} chars)"
    # Contains an issue category tag list (used as machine-readable categories)
    assert "category tag" in body.lower() or "issue category" in body.lower()


def test_bdd_review_flags_sequence_diagram():
    """User-flagged feature must be explicit in BDD reviewer rules."""
    body = (REVIEW / "bdd.review.md").read_text(encoding="utf-8")
    assert "sequence_diagram" in body
    assert "sequenceDiagram" in body


def test_spec_advanced_review_covers_db_redis():
    body = (REVIEW / "spec-advanced.review.md").read_text(encoding="utf-8")
    assert "redis" in body.lower()
    assert "sql" in body.lower() or "create_table" in body.lower()
    assert "mermaid" in body.lower()


def test_assets_review_aligns_with_resource_counts():
    body = (REVIEW / "assets.review.md").read_text(encoding="utf-8")
    assert "resource_counts" in body
