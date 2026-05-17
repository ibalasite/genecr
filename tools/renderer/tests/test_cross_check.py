"""Cross-step consistency checks — program-driven, no AI involved.

Counts must come from real parsing, not AI self-reports. Tests cover:
- Resource count alignment (spec-basic.resource_counts ↔ assets entries)
- Scenario count adequacy (bdd ≥ acceptance_criteria + api_endpoints)
- SQL index alignment (each WHERE/JOIN col walks an index)
- Redis key alignment (every accessed key declared in schema)
"""
from __future__ import annotations

import pytest

from cross_check import (
    Issue,
    check_redis_key_alignment,
    check_resource_counts,
    check_scenario_count,
    check_sql_index_alignment,
    run_all_checks,
)


# ─── resource counts ────────────────────────────────────────────────────────

def _spec_basic_with_counts(counts):
    return {
        "feature": {"name": "x", "slug": "x"},
        "resource_counts": counts,
    }


def _assets_with(entries):
    return {"feature": {"name": "x", "slug": "x"}, "assets": entries}


def test_resource_counts_match():
    sb = _spec_basic_with_counts({"images": 3, "sounds": 2})
    assets = _assets_with([
        {"id": "i1", "name": "a", "type": "image"},
        {"id": "i2", "name": "b", "type": "image"},
        {"id": "i3", "name": "c", "type": "image"},
        {"id": "s1", "name": "d", "type": "sound"},
        {"id": "s2", "name": "e", "type": "sound"},
    ])
    assert check_resource_counts(sb, assets) == []


def test_resource_counts_mismatch_too_few():
    sb = _spec_basic_with_counts({"images": 5})
    assets = _assets_with([
        {"id": "i1", "name": "a", "type": "image"},
        {"id": "i2", "name": "b", "type": "image"},
    ])
    issues = check_resource_counts(sb, assets)
    assert len(issues) == 1
    assert issues[0].step == "assets"
    assert "images" in issues[0].detail
    assert "5" in issues[0].detail and "2" in issues[0].detail


def test_resource_counts_mismatch_too_many():
    sb = _spec_basic_with_counts({"images": 1})
    assets = _assets_with([
        {"id": "i1", "name": "a", "type": "image"},
        {"id": "i2", "name": "b", "type": "image"},
    ])
    issues = check_resource_counts(sb, assets)
    assert len(issues) == 1
    assert "1" in issues[0].detail and "2" in issues[0].detail


def test_resource_counts_missing_category():
    sb = _spec_basic_with_counts({"images": 1, "sounds": 1})
    assets = _assets_with([
        {"id": "i1", "name": "a", "type": "image"},
    ])
    issues = check_resource_counts(sb, assets)
    cats = {i.detail for i in issues}
    assert any("sounds" in d for d in cats)


def test_resource_counts_dynamic_categories():
    """Works for ANY category — not hard-coded to images/sounds/animations."""
    sb = _spec_basic_with_counts({"images": 1, "particles": 2, "voiceover": 1})
    assets = _assets_with([
        {"id": "p1", "name": "p", "type": "particle"},
        {"id": "p2", "name": "q", "type": "particle"},
        {"id": "i1", "name": "i", "type": "image"},
        {"id": "v1", "name": "v", "type": "voiceover"},
    ])
    assert check_resource_counts(sb, assets) == []


def test_resource_counts_nested_dict_sums():
    """resource_counts can be nested: { images: {bg: 3, ui: 5} } → sum 8."""
    """Nested dict: per-sub-category check. assets must declare matching .category."""
    sb = _spec_basic_with_counts({"images": {"background": 2, "ui": 1}})
    assets = _assets_with([
        {"id": "1", "name": "x", "type": "image", "category": "background"},
        {"id": "2", "name": "y", "type": "image", "category": "background"},
        {"id": "3", "name": "z", "type": "image", "category": "ui"},
    ])
    assert check_resource_counts(sb, assets) == []


def test_nested_subcategory_count_mismatch_per_sub():
    """Nested dict: each sub-category checked independently."""
    sb = _spec_basic_with_counts({"images": {"background": 2, "ui": 5}})
    assets = _assets_with([
        {"id": "1", "name": "x", "type": "image", "category": "background"},
        {"id": "2", "name": "y", "type": "image", "category": "background"},
        {"id": "3", "name": "z", "type": "image", "category": "ui"},
    ])
    issues = check_resource_counts(sb, assets)
    assert any("'images.ui'" in i.detail and "declares 5" in i.detail and "has 1" in i.detail
               for i in issues)


def test_nested_undeclared_subcategory_flagged():
    """assets has a sub-category that spec-basic didn't declare → issue."""
    sb = _spec_basic_with_counts({"images": {"background": 1}})
    assets = _assets_with([
        {"id": "1", "name": "x", "type": "image", "category": "background"},
        {"id": "2", "name": "y", "type": "image", "category": "rogue_sub"},
    ])
    issues = check_resource_counts(sb, assets)
    assert any("rogue_sub" in i.detail and "not declared" in i.detail for i in issues)


def test_timeline_vs_scrum_points_aligned():
    from cross_check import check_timeline_vs_scrum_points
    sb = {"timeline": [{"duration_weeks": 2}]}
    scrum = {"stories": [{"points": p} for p in [2, 3, 2, 3]]}  # total 10 ≈ 2*5
    assert check_timeline_vs_scrum_points(sb, scrum) == []


def test_timeline_vs_scrum_points_mismatch():
    from cross_check import check_timeline_vs_scrum_points
    sb = {"timeline": [{"duration_weeks": 7}]}  # expects ~35 points
    scrum = {"stories": [{"points": 2}, {"points": 3}]}  # 5, way off
    issues = check_timeline_vs_scrum_points(sb, scrum)
    assert len(issues) == 1
    assert issues[0].step == "scrum"
    assert "timeline_scrum_mismatch" == issues[0].category


# ─── wireframe-anchored scope cap (objective formula) ──────────────────────

def test_scope_cap_passes_when_within_bounds():
    """6 wireframes → max 3 weeks / 15 points. Actual 2 weeks / 10 points OK."""
    from cross_check import check_scope_against_wireframes
    sb = {"wireframes": [{}] * 6, "timeline": [{"duration_weeks": 2}]}
    scrum = {"stories": [{"points": 2}] * 5}  # 10 points
    assert check_scope_against_wireframes(sb, scrum) == []


def test_scope_cap_flags_inflated_timeline():
    """6 wireframes → max 3 weeks; 7 weeks overshoots."""
    from cross_check import check_scope_against_wireframes
    sb = {"wireframes": [{}] * 6, "timeline": [{"duration_weeks": 7}]}
    scrum = {"stories": []}
    issues = check_scope_against_wireframes(sb, scrum)
    assert any("週" in i.detail and "7" in i.detail for i in issues)


def test_scope_cap_flags_inflated_points():
    """6 wireframes → max 15 points; 52 points overshoots."""
    from cross_check import check_scope_against_wireframes
    sb = {"wireframes": [{}] * 6, "timeline": [{"duration_weeks": 2}]}
    scrum = {"stories": [{"points": p} for p in [5, 8, 13, 8, 5, 13]]}  # 52
    issues = check_scope_against_wireframes(sb, scrum)
    assert any("點" in i.detail and "52" in i.detail for i in issues)


def test_scope_cap_catches_dual_inflation():
    """Both timeline AND points inflated — old ratio check missed this case
    (7 weeks * 5 = 35 expected vs 52 actual = 1.49x within ±50%)."""
    from cross_check import check_scope_against_wireframes
    sb = {"wireframes": [{}] * 6, "timeline": [{"duration_weeks": 7}]}
    scrum = {"stories": [{"points": p} for p in [5, 8, 13, 8, 5, 13]]}  # 52
    issues = check_scope_against_wireframes(sb, scrum)
    assert len(issues) >= 2  # both timeline AND points flagged


def test_resource_counts_no_counts_field_no_issue():
    """If spec-basic has no resource_counts, can't check — emit no issue
    (validation already enforces presence at production time)."""
    sb = {"feature": {"name": "x", "slug": "x"}}
    assets = _assets_with([{"id": "1", "name": "x", "type": "image"}])
    assert check_resource_counts(sb, assets) == []


# ─── scenario count ─────────────────────────────────────────────────────────

def test_scenario_count_adequate():
    bdd = {"scenarios": [{"id": str(i)} for i in range(5)]}
    sb = {"acceptance_criteria": ["a", "b"]}
    sa = {"apis": [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]}
    assert check_scenario_count(bdd, sb, sa) == []


def test_scenario_count_too_few():
    bdd = {"scenarios": [{"id": "1"}, {"id": "2"}]}
    sb = {"acceptance_criteria": ["a", "b", "c"]}
    sa = {"apis": [{"id": "a1"}, {"id": "a2"}]}
    issues = check_scenario_count(bdd, sb, sa)
    assert len(issues) == 1
    assert issues[0].step == "bdd"
    assert "5" in issues[0].detail  # 3 + 2 = 5 needed
    assert "2" in issues[0].detail  # got 2


def test_scenario_count_works_with_counts_object():
    """Alternative spec-basic shape: resource_counts.acceptance_criteria=N."""
    bdd = {"scenarios": [{"id": "1"}]}
    sb = {"resource_counts": {"acceptance_criteria": 3}}
    sa = {"counts": {"api_endpoints": 1}}
    issues = check_scenario_count(bdd, sb, sa)
    assert len(issues) == 1


# ─── SQL index alignment ────────────────────────────────────────────────────

def test_sql_index_alignment_pass():
    sa = {
        "data_models": [
            {
                "name": "users",
                "kind": "mysql",
                "fields": [],
                "indexes": ["PRIMARY KEY (uid)", "INDEX idx_email (email)"],
            }
        ],
        "db_queries": [
            {
                "scenario": "lookup by email",
                "sql": "SELECT * FROM users WHERE email = ?",
                "used_indexes": ["idx_email"],
            }
        ],
    }
    assert check_sql_index_alignment(sa) == []


def test_sql_where_col_not_in_any_index():
    sa = {
        "data_models": [
            {
                "name": "users",
                "kind": "mysql",
                "indexes": ["PRIMARY KEY (uid)"],
            }
        ],
        "db_queries": [
            {
                "scenario": "scan by nickname",
                "sql": "SELECT * FROM users WHERE nickname = ?",
            }
        ],
    }
    issues = check_sql_index_alignment(sa)
    assert len(issues) == 1
    assert issues[0].step == "spec-advanced"
    assert "nickname" in issues[0].detail


def test_sql_alignment_no_db_queries_no_issue():
    sa = {"data_models": []}
    assert check_sql_index_alignment(sa) == []


# ─── Redis key alignment ────────────────────────────────────────────────────

def test_redis_keys_all_declared():
    sa = {
        "data_models": [
            {"name": "user_level", "kind": "redis", "redis_pattern": "user:{uid}:level"}
        ],
        "redis_ops": [
            {
                "scenario": "read level",
                "commands": ["GET user:42:level"],
                "accessed_keys": ["user:{uid}:level"],
            }
        ],
    }
    assert check_redis_key_alignment(sa) == []


def test_redis_key_undeclared():
    sa = {
        "data_models": [
            {"name": "user_level", "kind": "redis", "redis_pattern": "user:{uid}:level"}
        ],
        "redis_ops": [
            {
                "scenario": "bug",
                "commands": ["GET session:abc"],
                "accessed_keys": ["session:{token}"],
            }
        ],
    }
    issues = check_redis_key_alignment(sa)
    assert len(issues) == 1
    assert "session:{token}" in issues[0].detail


def test_redis_alignment_no_ops_no_issue():
    assert check_redis_key_alignment({"data_models": []}) == []


# ─── orchestrator ───────────────────────────────────────────────────────────

def test_run_all_checks_routes_by_step():
    """When pipeline finishes step X, run_all_checks returns issues that
    require fixing step X (not earlier steps)."""
    all_data = {
        "spec-basic": _spec_basic_with_counts({"images": 5}),
        "assets": _assets_with([{"id": "1", "name": "x", "type": "image"}]),
    }
    issues = run_all_checks("assets", all_data)
    assert all(i.step == "assets" for i in issues)
    assert len(issues) >= 1


def test_run_all_checks_skips_unavailable_upstream():
    """If upstream data is missing (step hasn't run yet), don't crash."""
    issues = run_all_checks("assets", {"assets": _assets_with([])})
    assert isinstance(issues, list)  # no crash


def test_issue_serialization():
    """Issues must be JSON-serializable for passing to fixer subagent."""
    import json
    issue = Issue(step="assets", category="count_mismatch", detail="x")
    s = json.dumps(issue.to_dict())
    assert "assets" in s
    assert "count_mismatch" in s
