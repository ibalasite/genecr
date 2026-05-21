"""TDD: dryrun.resource_counts.* + dryrun.test_counts.* 取代 resource_counts 美術欄位。

第一性原則：
- dryrun.resource_counts.* 是美術資源唯一 SSOT，resource_counts 頂層美術欄位移除
- dryrun.test_counts.acceptance_criteria 是 acceptance_criteria 計數唯一 SSOT
- cross_check / render 所有讀取點必須改讀 dryrun.*，不准再讀 resource_counts 美術欄位
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "tools" / "renderer") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))


def _sb(*, dryrun_rc=None, dryrun_tc=None, dryrun_tech=None, old_rc=None, wireframes=None, acceptance_criteria=None):
    """Construct a minimal spec-basic dict."""
    sb = {"feature": {"name": "x", "slug": "x"}}
    dryrun = {}
    if dryrun_rc is not None:
        dryrun["resource_counts"] = dryrun_rc
    if dryrun_tc is not None:
        dryrun["test_counts"] = dryrun_tc
    if dryrun_tech is not None:
        dryrun["tech_counts"] = dryrun_tech
    if dryrun:
        sb["dryrun"] = dryrun
    if old_rc is not None:
        sb["resource_counts"] = old_rc
    if wireframes is not None:
        sb["wireframes"] = wireframes
    if acceptance_criteria is not None:
        sb["acceptance_criteria"] = acceptance_criteria
    return sb


def _assets(*types):
    return {"assets": [{"id": f"a{i}", "name": f"n{i}", "type": t} for i, t in enumerate(types)]}


# ─── check_resource_counts ───────────────────────────────────────────────────

class TestCheckResourceCountsReadsDryrun:
    """check_resource_counts 必須從 dryrun.resource_counts 讀，不從頂層 resource_counts。"""

    def test_reads_dryrun_resource_counts(self):
        from cross_check import check_resource_counts
        sb = _sb(dryrun_rc={"image": 2})
        assets = _assets("image", "image")
        assert check_resource_counts(sb, assets) == []

    def test_ignores_old_resource_counts_art_fields(self):
        """若只在頂層 resource_counts 宣告美術欄位，cross_check 不應看到它（已移除）。"""
        from cross_check import check_resource_counts
        # 只放在舊位置，dryrun.resource_counts 沒有 → check_resource_counts 應回空（沒東西可比）
        sb = _sb(old_rc={"image": 2})
        assets = _assets("image", "image")
        # 舊欄位已移除，check_resource_counts 讀 dryrun.resource_counts（None）→ 早返回 []
        assert check_resource_counts(sb, assets) == []

    def test_dryrun_rc_mismatch_flagged(self):
        from cross_check import check_resource_counts
        sb = _sb(dryrun_rc={"image": 5})
        assets = _assets("image", "image")
        issues = check_resource_counts(sb, assets)
        assert len(issues) == 1
        assert "5" in issues[0].detail and "2" in issues[0].detail


# ─── _per_role_points_anchor ─────────────────────────────────────────────────

class TestPerRoleAnchorReadsDryrun:
    """_per_role_points_anchor art/planner 點數讀 dryrun.resource_counts / dryrun.test_counts。"""

    def test_art_points_from_dryrun_resource_counts(self):
        from cross_check import _per_role_points_anchor, _ANCHOR_ART
        sb = _sb(
            dryrun_rc={"visual_total": 43, "audio_total": 0},
            dryrun_tech={"api_endpoints": 0, "db_tables": 0, "redis_keys": 0},
        )
        result = _per_role_points_anchor(sb)
        expected_art = 43 * _ANCHOR_ART[0] / _ANCHOR_ART[1]
        assert abs(result["art"] - expected_art) < 0.01

    def test_art_zero_when_old_rc_only(self):
        """dryrun.resource_counts 不存在 → art = 0，不讀舊 resource_counts。"""
        from cross_check import _per_role_points_anchor
        sb = _sb(old_rc={"visual_total": 43, "audio_total": 0})
        result = _per_role_points_anchor(sb)
        assert result["art"] == 0.0

    def test_planner_points_from_dryrun_test_counts(self):
        from cross_check import _per_role_points_anchor, _ANCHOR_PLANNER
        sb = _sb(
            dryrun_rc={"visual_total": 0, "audio_total": 0},
            dryrun_tc={"acceptance_criteria": 12},
            dryrun_tech={"api_endpoints": 0, "db_tables": 0, "redis_keys": 0},
        )
        result = _per_role_points_anchor(sb)
        expected = 12 * _ANCHOR_PLANNER[0] / _ANCHOR_PLANNER[1]
        assert abs(result["planner"] - expected) < 0.01

    def test_planner_zero_when_old_rc_acceptance_criteria_only(self):
        """resource_counts.acceptance_criteria 舊欄位不應影響 planner 點數。"""
        from cross_check import _per_role_points_anchor
        sb = _sb(old_rc={"acceptance_criteria": 12})
        result = _per_role_points_anchor(sb)
        assert result["planner"] == 0.0


# ─── _role_budget_days ───────────────────────────────────────────────────────

class TestRoleBudgetReadsDryrun:
    """_role_budget_days art budget 讀 dryrun.resource_counts。"""

    def test_art_budget_from_dryrun_resource_counts(self):
        from cross_check import _role_budget_days
        rc = {"image": {"bg": 10, "ui": 5}, "animation": {"c": 3}, "sound": {"d": 6}}
        sb = _sb(
            dryrun_rc=rc,
            dryrun_tech={"api_endpoints": 8},
            wireframes=[{"name": f"w{i}"} for i in range(6)],
        )
        budget = _role_budget_days(sb)
        expected_art = (10 + 5 + 3 + 6) * 0.2
        assert abs(budget["art"] - expected_art) < 0.01

    def test_art_zero_when_dryrun_rc_absent(self):
        """dryrun.resource_counts 缺 → art = 0。"""
        from cross_check import _role_budget_days
        sb = _sb(
            old_rc={"image": {"bg": 10}},
            dryrun_tech={"api_endpoints": 8},
            wireframes=[{"name": "w1"}],
        )
        budget = _role_budget_days(sb)
        assert budget["art"] == 0.0


# ─── check_assets_matches_sb_totals ─────────────────────────────────────────

class TestAssetsMatchesSbReadsDryrun:
    """check_assets_matches_sb_totals 必須讀 dryrun.resource_counts.visual_total/audio_total。"""

    def test_reads_dryrun_totals_match(self):
        from cross_check import check_assets_matches_sb_totals
        sb = _sb(dryrun_rc={"visual_total": 2, "audio_total": 1})
        assets = _assets("image", "image", "sound")
        assert check_assets_matches_sb_totals(sb, assets) == []

    def test_reads_dryrun_totals_mismatch(self):
        from cross_check import check_assets_matches_sb_totals
        sb = _sb(dryrun_rc={"visual_total": 5, "audio_total": 0})
        assets = _assets("image", "image")
        issues = check_assets_matches_sb_totals(sb, assets)
        assert any("visual" in i.detail for i in issues)
        assert any("dryrun.resource_counts" in i.detail for i in issues)

    def test_ignores_old_resource_counts_totals(self):
        """若 dryrun.resource_counts 不存在，check 不應讀舊 resource_counts。"""
        from cross_check import check_assets_matches_sb_totals
        sb = _sb(old_rc={"visual_total": 5, "audio_total": 0})
        assets = _assets("image", "image")
        # 舊位置已移除 → check 應早返回 []（無可比數字）
        assert check_assets_matches_sb_totals(sb, assets) == []


# ─── _get_acceptance_count ───────────────────────────────────────────────────

class TestGetAcceptanceCountReadsDryrunTestCounts:
    """_get_acceptance_count 必須讀 dryrun.test_counts.acceptance_criteria。"""

    def test_reads_dryrun_test_counts(self):
        from cross_check import _get_acceptance_count
        sb = _sb(dryrun_tc={"acceptance_criteria": 7})
        assert _get_acceptance_count(sb) == 7

    def test_ignores_old_resource_counts_acceptance_criteria(self):
        from cross_check import _get_acceptance_count
        sb = _sb(old_rc={"acceptance_criteria": 99})
        assert _get_acceptance_count(sb) == 0

    def test_ignores_sb_acceptance_criteria_array(self):
        """acceptance_criteria 陣列只是來源列表，計數必須明確宣告在 dryrun.test_counts。"""
        from cross_check import _get_acceptance_count
        sb = _sb(acceptance_criteria=[{"desc": "x"}, {"desc": "y"}])
        # 沒有 dryrun.test_counts → 應回 0（不自動 len()）
        assert _get_acceptance_count(sb) == 0


# ─── render.preprocess spec-basic ────────────────────────────────────────────

class TestRenderPreprocessReadsDryrun:
    """render.preprocess('spec-basic') 必須從 dryrun.resource_counts 取 visual/audio_total。"""

    def test_reads_dryrun_resource_counts(self, tmp_path):
        import render
        data = {
            "feature": {"name": "f", "slug": "f"},
            "dryrun": {
                "resource_counts": {
                    "visual_total": 15,
                    "audio_total": 4,
                }
            },
            "resource_counts": {},
        }
        out = render.preprocess("spec-basic", dict(data), tmp_path)
        assert out["resource_summary"]["visual_total"] == 15
        assert out["resource_summary"]["audio_total"] == 4
        assert out["resource_summary"]["total"] == 19

    def test_old_resource_counts_totals_ignored(self, tmp_path):
        """舊 resource_counts.visual_total 不再被 render 讀取。"""
        import render
        data = {
            "feature": {"name": "f", "slug": "f"},
            "resource_counts": {
                "visual_total": 99,
                "audio_total": 99,
            },
        }
        out = render.preprocess("spec-basic", dict(data), tmp_path)
        # dryrun.resource_counts 不存在 → visual=0, audio=0
        assert out["resource_summary"]["visual_total"] == 0
        assert out["resource_summary"]["audio_total"] == 0
