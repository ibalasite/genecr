"""spec-basic 純自洽守門：禁止跨 doc + 三層 (prompt/review/cross_check) 同規則。

歷史錯誤：check_timeline_against_formula(sb, sa, assets) /
check_wireframe_coverage(sb, sa, scrum) 為了「公式好看」偷讀下游 sibling，
fresh-feature 從零生時下游不存在 → check broken。spec-basic 自己手上的
bookkeeping (resource_counts.api_endpoints / admin_journey / wireframes /
sections) 就該夠用，沒就補 schema 欄位讓 AI 自報。
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = REPO_ROOT / "templates"

if str(REPO_ROOT / "tools" / "renderer") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))


# ─── A. 跨 doc check 已刪 ────────────────────────────────────────────────


def test_check_timeline_signature_takes_only_sb():
    from cross_check import check_timeline_against_formula
    params = inspect.signature(check_timeline_against_formula).parameters
    forbidden = {"spec_advanced", "sa", "assets_data", "assets"}
    leaked = set(params) & forbidden
    assert not leaked, f"check_timeline must take only sb; sa/assets leaked: {leaked}"


def test_check_wireframe_coverage_removed():
    import cross_check
    assert not hasattr(cross_check, "check_wireframe_coverage"), (
        "check_wireframe_coverage 跨 doc 版本必須整個刪除，自洽版用 check_admin_wireframe_self_consistency"
    )


# ─── B. 純 sb self-check 正確性 ─────────────────────────────────────────


def test_role_budget_uses_sb_resource_counts_only():
    from cross_check import _role_budget_days
    sb = {
        "wireframes": [{"name": f"w{i}"} for i in range(6)],
        "user_journey": [{"action": "a"}] * 3,
        "admin_journey": [{"action": "a"}] * 2,
        "resource_counts": {
            "api_endpoints": 8,
            "image": {"a": 10, "b": 5},
            "animation": {"c": 3},
            "sound": {"d": 6},
        },
    }
    budget = _role_budget_days(sb)
    assert budget["server_engineer"] == pytest.approx(8.0)
    assert budget["art"] == pytest.approx(4.8, abs=0.1)
    assert "po" not in budget


def test_timeline_check_works_without_any_sibling():
    """Pure spec-basic input — timeline check still runs & flags correctly."""
    from cross_check import check_timeline_against_formula
    sb = {
        "wireframes": [{"name": "w"}] * 6,
        "resource_counts": {"api_endpoints": 8, "image": {"x": 10}},
        "timeline": [{"phase": "MVP", "duration_weeks": 1}],  # underestimated
        "user_journey": [{"action": "a"}] * 3,
        "admin_journey": [],
    }
    issues = check_timeline_against_formula(sb)
    cats = {i.category for i in issues}
    assert "timeline_underestimated" in cats


# ─── C. admin self-consistency 雙向 ──────────────────────────────────────


def test_admin_journey_without_admin_wf_flags():
    from cross_check import check_admin_wireframe_self_consistency
    sb = {
        "admin_journey": [{"action": "建立活動"}],
        "wireframes": [{"name": "玩家 — 主畫面"}],  # 無 admin wireframe
    }
    issues = check_admin_wireframe_self_consistency(sb)
    cats = {i.category for i in issues}
    assert "admin_wireframe_missing_for_journey" in cats


def test_admin_wf_without_admin_journey_flags():
    from cross_check import check_admin_wireframe_self_consistency
    sb = {
        "admin_journey": [],
        "wireframes": [{"name": "後台 — 玩家記錄"}],
    }
    issues = check_admin_wireframe_self_consistency(sb)
    cats = {i.category for i in issues}
    assert "admin_journey_missing" in cats


def test_both_present_passes():
    from cross_check import check_admin_wireframe_self_consistency
    sb = {
        "admin_journey": [{"action": "建立活動"}],
        "wireframes": [{"name": "後台 — 活動設定"}],
    }
    assert check_admin_wireframe_self_consistency(sb) == []


# ─── D. 三層一致性（grep-based） ───────────────────────────────────────


def test_timeline_formula_documented_in_prompt():
    text = (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")
    assert "ceil(max" in text or "ceil（max" in text or "無條件進位" in text, (
        "prompt 必須說明 timeline_weeks = ceil(max(per-role-days)/5)"
    )
    assert "api_endpoints" in text, "prompt 必須教 AI 寫 resource_counts.api_endpoints 自報數"


def test_timeline_rule_in_review_md():
    text = (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")
    assert text.count("timeline_overestimated") >= 2  # rule def + whitelist
    assert text.count("timeline_underestimated") >= 2


def test_admin_self_consistency_rule_in_three_layers():
    prompt_text = (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")
    review_text = (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")
    code_text = (REPO_ROOT / "tools" / "renderer" / "cross_check.py").read_text(encoding="utf-8")

    # prompt: 教 AI 雙向規則
    assert "admin_journey" in prompt_text and "wireframe" in prompt_text

    # review.md: 兩條 rule
    assert review_text.count("admin_journey_missing") >= 2
    assert review_text.count("admin_wireframe_missing_for_journey") >= 2

    # cross_check: function 存在
    assert "check_admin_wireframe_self_consistency" in code_text


# ─── E. 隔離：mock 全 sibling 也不准影響 spec-basic ─────────────────────


def test_pipeline_orchestrated_no_downstream_to_spec_basic_check(tmp_path):
    """spec-basic 重跑時，cross_check_fn 收到的 all_step_data 不含下游 keys."""
    from pipeline_orchestrated import _load_all_upstream
    # 寫所有 7 個 sibling
    for name in ("spec-basic", "spec-advanced", "assets", "bdd", "scrum", "prototype", "docs"):
        (tmp_path / f"{name}.input.json").write_text('{"feature":{"name":"f"}}', encoding="utf-8")
    # spec-basic depends_on = []
    upstream = _load_all_upstream("spec-basic", tmp_path, depends_on=[])
    assert upstream == {}, f"spec-basic 不該看到任何 sibling; got {list(upstream.keys())}"


def test_pipeline_orchestrated_no_upstream_for_check_bypass():
    """確認 pipeline_orchestrated.py 沒留我之前那個 upstream_for_check 後門."""
    text = (REPO_ROOT / "tools" / "renderer" / "pipeline_orchestrated.py").read_text(encoding="utf-8")
    assert "upstream_for_check" not in text, (
        "upstream_for_check (depends_on=None bypass) 必須刪除"
    )


# ─── F. 品質 baseline（本 case） ───────────────────────────────────────


def test_current_run_passes_self_check():
    """Golden baseline: current spec-basic.input.json 對純 sb self-check 必過."""
    run_dir = REPO_ROOT / "output" / "checkin7v2" / "20260516-223523"
    sb_path = run_dir / "spec-basic.input.json"
    if not sb_path.exists():
        pytest.skip("baseline spec-basic.input.json not present")
    sb = json.loads(sb_path.read_text(encoding="utf-8"))

    from cross_check import (check_timeline_against_formula,
                              check_admin_wireframe_self_consistency)
    issues = check_timeline_against_formula(sb) + check_admin_wireframe_self_consistency(sb)
    cats = {i.category for i in issues}
    # Both should be clean for current baseline (timeline 2 weeks, admin 兩個都有)
    assert "timeline_underestimated" not in cats
    assert "timeline_overestimated" not in cats
    assert "admin_journey_missing" not in cats
    assert "admin_wireframe_missing_for_journey" not in cats
