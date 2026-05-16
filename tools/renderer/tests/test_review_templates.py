"""Reviewer/fixer prompt skeletons enforce strict structure; every step's
review.md follows the same uniform format (rules + category whitelist)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS = REPO_ROOT / "templates" / "prompts"
REVIEW = REPO_ROOT / "templates" / "review"

ALL_STEPS = [
    "spec-basic", "spec-advanced", "assets",
    "bdd", "scrum", "prototype", "docs",
]


def test_reviewer_skeleton_enforces_strict_constraints():
    body = (PROMPTS / "_review.prompt.md").read_text(encoding="utf-8")
    assert "INDEPENDENT REVIEWER" in body
    # Hard constraints the skeleton must enforce
    assert "SCOPE LOCK" in body
    assert "CITE REAL PATHS" in body
    assert "CATEGORY WHITELIST" in body
    assert "NO SCOPE CREEP" in body
    assert "NO HALLUCINATION" in body
    # Placeholders the orchestrator fills
    for ph in ("{step_review_rules}", "{input_data}", "{upstream_outputs}", "{step_type}"):
        assert ph in body, f"reviewer skeleton missing placeholder {ph}"
    # Output shape with rule/category/path/detail
    for k in ('"rule"', '"category"', '"path"', '"detail"'):
        assert k in body, f"reviewer output shape missing key {k}"


def test_fixer_skeleton_enforces_strict_execution():
    body = (PROMPTS / "_fixer.prompt.md").read_text(encoding="utf-8")
    assert "INDEPENDENT FIXER" in body
    # Hard constraints
    assert "FIX EVERY LISTED ISSUE" in body
    assert "DO NOT TOUCH ANYTHING NOT LISTED" in body
    assert "OUTPUT IS COMPLETE" in body
    assert "NEVER DROP REQUIRED FIELDS" in body
    assert "NEVER INVENT FIELDS" in body
    assert "COUNT MISMATCHES" in body and "UPSTREAM" in body
    # Placeholders
    for ph in ("{step_type}", "{input_data}", "{issues}", "{upstream_outputs}"):
        assert ph in body, f"fixer skeleton missing placeholder {ph}"


# ── uniform review.md format ────────────────────────────────────────────────

_RULE_HEADER = re.compile(r"###\s+R(\d+)\s+—\s+`([a-z0-9_]+)`")


@pytest.mark.parametrize("step", ALL_STEPS)
def test_review_md_uses_numbered_rules(step):
    body = (REVIEW / f"{step}.review.md").read_text(encoding="utf-8")
    rules = _RULE_HEADER.findall(body)
    assert rules, f"{step}.review.md has no R<n> — `tag` headers"
    # Numbers are 1..N contiguous starting at 1
    nums = [int(n) for n, _ in rules]
    assert nums == list(range(1, len(nums) + 1)), (
        f"{step} rule numbering not contiguous: {nums}"
    )


@pytest.mark.parametrize("step", ALL_STEPS)
def test_review_md_has_category_whitelist(step):
    body = (REVIEW / f"{step}.review.md").read_text(encoding="utf-8")
    assert "ISSUE CATEGORY TAGS" in body, f"{step}.review.md missing whitelist heading"
    # Whitelist contains a dash-list of `tag` entries
    whitelist_section = body.split("ISSUE CATEGORY TAGS")[1]
    listed = re.findall(r"-\s+`([a-z0-9_]+)`", whitelist_section)
    assert listed, f"{step}.review.md whitelist has no tags"


@pytest.mark.parametrize("step", ALL_STEPS)
def test_review_md_rule_tags_match_whitelist(step):
    """Every category tag used in a rule header must appear in the whitelist."""
    body = (REVIEW / f"{step}.review.md").read_text(encoding="utf-8")
    rule_tags = {tag for _, tag in _RULE_HEADER.findall(body)}
    whitelist_section = body.split("ISSUE CATEGORY TAGS")[1]
    whitelist = set(re.findall(r"-\s+`([a-z0-9_]+)`", whitelist_section))
    missing = rule_tags - whitelist
    assert not missing, f"{step} rule tags not in whitelist: {missing}"


@pytest.mark.parametrize("step", ALL_STEPS)
def test_review_md_every_rule_has_check_and_fail_when(step):
    body = (REVIEW / f"{step}.review.md").read_text(encoding="utf-8")
    sections = re.split(r"###\s+R\d+\s+—\s+", body)[1:]  # skip preamble
    for i, sect in enumerate(sections, 1):
        # Stop at the next h2 to avoid greedy match across the whole tail
        sect_body = sect.split("\n## ")[0]
        assert "Check:" in sect_body, f"{step} rule R{i} missing 'Check:'"
        assert "Fail when:" in sect_body, f"{step} rule R{i} missing 'Fail when:'"


def test_bdd_review_includes_sequence_diagram_required():
    body = (REVIEW / "bdd.review.md").read_text(encoding="utf-8")
    assert "sequence_diagram_missing" in body
    assert "user-flagged" in body.lower() or "critical" in body.lower()


def test_assets_review_aligns_with_resource_counts():
    body = (REVIEW / "assets.review.md").read_text(encoding="utf-8")
    assert "resource_counts" in body
    assert "type_not_in_vocabulary" in body


def test_spec_advanced_review_covers_db_redis_sql():
    body = (REVIEW / "spec-advanced.review.md").read_text(encoding="utf-8")
    for tag in ("schema_field_index_mismatch", "sql_no_matching_index",
                "redis_command_type_mismatch", "mermaid_invalid"):
        assert tag in body, f"spec-advanced missing tag {tag}"
