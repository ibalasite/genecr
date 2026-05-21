"""scrum 升級成 Epic + 2-3 Stories per Role 結構（選項 B）。

校準錨點（依本 case 反推 day/item coef）：
- art: 0.2 × asset_count
- server_engineer: 1.0 × api_count
- client_engineer: 0.67 × wireframe_count
- planner: 0.2 × spec_section_count

cap：per-story ≤ 5 pt、per-role 加總 ≤ 10 pt（4 主要 role 平行做）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = REPO_ROOT / "templates"

if str(REPO_ROOT / "tools" / "renderer") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))


# ─── Schema upgrades ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def scrum_schema() -> dict:
    return json.loads((TEMPLATES / "schemas" / "scrum.schema.json").read_text(encoding="utf-8"))


def test_schema_has_epics_field(scrum_schema):
    assert "epics" in scrum_schema["properties"], "scrum schema must declare top-level epics"
    epic_item = scrum_schema["properties"]["epics"]["items"]
    for f in ("id", "owner_role", "title"):
        assert f in epic_item["required"], f"epic items must require {f}"


def test_schema_story_requires_epic_field(scrum_schema):
    required = scrum_schema["properties"]["stories"]["items"]["required"]
    assert "epic" in required, "story must require `epic` reference field"


def test_schema_story_requires_subtasks_field(scrum_schema):
    item = scrum_schema["properties"]["stories"]["items"]
    assert "subtasks" in item["required"], "story must require `subtasks`"
    sub_schema = item["properties"]["subtasks"]
    assert sub_schema.get("type") == "array"
    assert sub_schema.get("minItems", 0) >= 1, "subtasks must have minItems >= 1"


def test_schema_story_points_enum_max_5(scrum_schema):
    points = scrum_schema["properties"]["stories"]["items"]["properties"]["points"]
    assert set(points["enum"]) == {1, 2, 3, 5}, (
        f"story points enum must be [1,2,3,5] (no 8/13 — per-story cap 5); got {points['enum']}"
    )


def test_schema_owner_role_enum_no_po(scrum_schema):
    # Story owner_role enum
    story_role = scrum_schema["properties"]["stories"]["items"]["properties"]["owner_role"]
    assert "po" not in story_role["enum"], "story owner_role enum must exclude po"
    assert set(story_role["enum"]) == {"server_engineer", "client_engineer", "planner", "art"}
    # Epic owner_role same constraint
    epic_role = scrum_schema["properties"]["epics"]["items"]["properties"]["owner_role"]
    assert "po" not in epic_role["enum"]


# ─── Per-role budget calibration ─────────────────────────────────────────


def test_role_budget_uses_calibrated_coef():
    """_role_budget_days now takes ONLY sb (pure self-contained)."""
    from cross_check import _role_budget_days
    sb = {
        "wireframes": [{"name": f"wf{i}"} for i in range(6)],
        "user_journey": [{"action": "a"}] * 3,
        "admin_journey": [{"action": "a"}] * 2,
        "matrix": {"rows": [{"label": "r"}] * 2},
        "resource_counts": {
            "image": {"x": 30, "y": 13},
        },
        "dryrun": {"tech_counts": {"api_endpoints": 8}},
    }
    budget = _role_budget_days(sb)
    assert "po" not in budget, "po must not appear in role budget dict"
    assert budget["art"] == pytest.approx(8.6, abs=0.01), f"art expected 8.6 got {budget.get('art')}"
    assert budget["server_engineer"] == pytest.approx(8.0, abs=0.01)
    assert budget["client_engineer"] == pytest.approx(4.02, abs=0.05)
    assert 0.5 <= budget["planner"] <= 2.5


def test_role_budget_uses_sb_bookkeeping_without_sibling():
    """sb only: no sa/assets — formula uses resource_counts bookkeeping."""
    from cross_check import _role_budget_days
    sb = {
        "wireframes": [{"name": "wf"}] * 3,
        "resource_counts": {
            "image": {"a": 10, "b": 5},
            "sound": {"c": 6},
        },
        "dryrun": {"tech_counts": {"api_endpoints": 5}},
    }
    budget = _role_budget_days(sb)
    assert budget["art"] == pytest.approx(4.2, abs=0.1)  # 0.2 × 21
    assert budget["server_engineer"] == pytest.approx(5.0, abs=0.01)  # 1.0 × 5


# ─── Per-role cap & per-story cap ────────────────────────────────────────


def test_check_role_points_overshoot_allowed():
    """地板邏輯：scrum 加總 > formula 地板 = 合法（Fibonacci 自然溢出）"""
    from cross_check import check_per_role_points_floor
    scrum = {"stories": [
        {"id": "S1", "owner_role": "art", "points": 5},
        {"id": "S2", "owner_role": "art", "points": 5},
        {"id": "S3", "owner_role": "art", "points": 3},
    ]}  # 13 點，formula 地板 10 → 13 ≥ 10 通過
    formula = {"server_engineer": 0, "art": 10, "client_engineer": 0, "planner": 0}
    issues = check_per_role_points_floor(scrum, formula)
    cats = {i.category for i in issues}
    assert "role_points_below_floor" not in cats


def test_check_role_points_below_floor_flags():
    """scrum 加總 < formula 地板 → 報 role_points_below_floor"""
    from cross_check import check_per_role_points_floor
    scrum = {"stories": [{"id": "S1", "owner_role": "art", "points": 1}]}
    formula = {"server_engineer": 0, "art": 8.0, "client_engineer": 0, "planner": 0}
    issues = check_per_role_points_floor(scrum, formula)
    cats = {i.category for i in issues}
    assert "role_points_below_floor" in cats


def test_check_story_size_flags_over_5():
    from cross_check import check_per_story_points_cap
    scrum = {"stories": [{"id": "S1", "owner_role": "art", "points": 8}]}
    issues = check_per_story_points_cap(scrum)
    cats = {i.category for i in issues}
    assert "story_too_large_split_needed" in cats


def test_check_epic_role_coverage_flags_missing():
    from cross_check import check_epic_role_coverage
    scrum = {"epics": [
        {"id": "E-srv", "owner_role": "server_engineer"},
        {"id": "E-cli", "owner_role": "client_engineer"},
        # art + planner missing
    ]}
    issues = check_epic_role_coverage(scrum)
    cats = {i.category for i in issues}
    assert "epic_role_missing" in cats
    details = " ".join(i.detail for i in issues)
    assert "art" in details and "planner" in details


def test_check_stories_belong_to_epic_flags_dangling():
    from cross_check import check_stories_belong_to_epic
    scrum = {
        "epics": [{"id": "E-srv", "owner_role": "server_engineer"}],
        "stories": [{"id": "S1", "epic": "E-NONEXISTENT", "owner_role": "server_engineer"}],
    }
    issues = check_stories_belong_to_epic(scrum)
    cats = {i.category for i in issues}
    assert "story_no_epic_link" in cats


def test_check_no_po_stories_flags():
    from cross_check import check_no_po_stories
    scrum = {"stories": [{"id": "S1", "owner_role": "po"}]}
    issues = check_no_po_stories(scrum)
    cats = {i.category for i in issues}
    assert "po_owner_role_used" in cats


def test_check_story_missing_subtasks_flags():
    from cross_check import check_story_has_subtasks
    scrum = {"stories": [{"id": "S1", "owner_role": "art", "subtasks": []}]}
    issues = check_story_has_subtasks(scrum)
    cats = {i.category for i in issues}
    assert "story_missing_subtasks" in cats


def test_timeline_uses_max_role_days_ceiled():
    """Elapsed weeks = ceil(max(per-role days) / 5) — 整週進位."""
    from cross_check import _elapsed_weeks_from_role_budget
    budget = {"server_engineer": 8.0, "client_engineer": 4.0, "art": 8.6, "planner": 1.0}
    wk = _elapsed_weeks_from_role_budget(budget)
    # max = 8.6 → ceil(8.6/5) = ceil(1.72) = 2 wk
    assert wk == 2, f"expected 2 (ceil), got {wk}"


def test_timeline_ceiling_on_exact_boundary():
    """max=10 → 10/5=2.0 → ceil=2 (not 3)."""
    from cross_check import _elapsed_weeks_from_role_budget
    assert _elapsed_weeks_from_role_budget({"x": 10}) == 2
    assert _elapsed_weeks_from_role_budget({"x": 11}) == 3   # 11/5=2.2 → ceil=3


def test_check_timeline_flags_underestimate():
    """spec-basic timeline 1 week < ceil expected 2 weeks → flag.
    純 sb（不傳 sa/assets）— 用 sb.dryrun.tech_counts.api_endpoints / wireframes 自報數。"""
    from cross_check import check_timeline_against_formula
    sb = {"wireframes": [{"name": f"w{i}"} for i in range(6)],
          "timeline": [{"phase": "MVP", "duration_weeks": 1}],
          "resource_counts": {"image": {"x": 43}},
          "dryrun": {"tech_counts": {"api_endpoints": 8}}}
    issues = check_timeline_against_formula(sb)
    cats = {i.category for i in issues}
    assert "timeline_underestimated" in cats


def test_check_timeline_passes_at_exact_expected():
    """timeline=2wk matches ceil(8.6/5)=2 → no issue. 純 sb."""
    from cross_check import check_timeline_against_formula
    sb = {"wireframes": [{"name": f"w{i}"} for i in range(6)],
          "timeline": [{"phase": "MVP", "duration_weeks": 2}],
          "resource_counts": {"image": {"x": 43}},
          "dryrun": {"tech_counts": {"api_endpoints": 8}}}
    issues = check_timeline_against_formula(sb)
    assert not issues


# ─── Render groups by epic + shows subtasks ──────────────────────────────


def test_render_groups_stories_under_epics():
    import render
    ex = {
        "feature": {"name": "f", "slug": "f"},
        "epic": "<deprecated>",
        "groups": [],
        "epics": [
            {"id": "E-srv", "owner_role": "server_engineer", "title": "後端", "description": "x"},
        ],
        "stories": [
            {"id": "S-01", "epic": "E-srv", "owner_role": "server_engineer",
             "title": "資料表", "role": "後端", "want": "a", "benefit": "b",
             "acceptance": ["a"], "points": 3, "subtasks": ["t1", "t2"]},
        ],
    }
    md = render.render("scrum", ex)
    # Epic header appears before story
    assert "E-srv" in md or "後端" in md, "epic header should appear in render"
    assert "S-01" in md and "資料表" in md, "story under epic"


def test_render_shows_subtasks_per_story():
    import render
    ex = {
        "feature": {"name": "f", "slug": "f"},
        "epic": "<deprecated>",
        "groups": [],
        "epics": [{"id": "E-art", "owner_role": "art", "title": "美術", "description": "x"}],
        "stories": [
            {"id": "S-01", "epic": "E-art", "owner_role": "art",
             "title": "圖", "role": "美術", "want": "a", "benefit": "b",
             "acceptance": ["a"], "points": 3,
             "subtasks": ["建立 D1 格子圖", "建立 D2 格子圖", "建立 banner"]},
        ],
    }
    md = render.render("scrum", ex)
    assert "建立 D1 格子圖" in md, "subtask must render in story block"
    assert "建立 banner" in md


# ─── Canonical example ─────────────────────────────────────────────────


def test_canonical_has_4_epics_and_no_po_story():
    ex = json.loads((TEMPLATES / "examples" / "scrum.input.json").read_text(encoding="utf-8"))
    epics = ex.get("epics", [])
    owners = {e["owner_role"] for e in epics}
    assert owners == {"server_engineer", "client_engineer", "planner", "art"}, (
        f"canonical must have 4 epics covering all 4 main roles; got {owners}"
    )
    for s in ex.get("stories", []):
        assert s.get("owner_role") != "po", f"canonical has po story: {s.get('id')}"
        assert s.get("epic"), f"canonical story {s.get('id')} missing epic ref"
        assert s.get("subtasks"), f"canonical story {s.get('id')} missing subtasks"
        assert s.get("points") <= 5, f"canonical story {s.get('id')} points > 5"
