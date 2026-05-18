"""Admin / 後台 UI coverage must not be silently dropped.

History: scrum story #5 mentioned 「後台 UI(活動設定面板+玩家記錄列表)」 and
spec-advanced had `/api/v1/admin/checkin/players`, but spec-basic.wireframes
collapsed admin into one entry (skipping the players-records screen) — the
prompt's "3-6 entries" cap + player-facing examples + no admin coverage rule
let it slip through. prototype prompt was even more restrictive — hardcoded
mobile 375px viewport, walked only user_journey, no admin demo possible.

These tests guard the two layers:
- spec-basic: every admin/internal API + every UI-implying scrum story must
  have a wireframe entry
- prototype: when spec-basic has admin wireframes, prototype_html must
  contain admin/desktop demo markers
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


# ─── 1-3. check_wireframe_coverage 已刪除（跨 doc 違規） ────────────────
# 取代：spec-basic 內部 admin self-consistency 檢查（admin_journey ↔ admin
# wireframe 雙向），測試在 test_spec_basic_self_check.py。
# 跨 doc 版本不會搬到下游 step — 違反「step 重跑不准依賴下游」。


@pytest.mark.skip(reason="check_wireframe_coverage 跨 doc 版本已刪除 — 取代為 check_admin_wireframe_self_consistency (純 sb 內部) 見 test_spec_basic_self_check.py")
def test_check_wireframe_coverage_flags_admin_api_without_wireframe():
    pass


@pytest.mark.skip(reason="同上 — cross-doc check 已刪")
def test_check_wireframe_coverage_passes_when_admin_api_has_matching_wireframe():
    pass


@pytest.mark.skip(reason="同上 — cross-doc check 已刪")
def test_check_wireframe_coverage_flags_scrum_ui_story_without_wireframe():
    pass


# ─── 4. spec-basic review.md whitelist ───────────────────────────────────


def test_spec_basic_review_md_has_admin_wireframe_rules():
    text = (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")
    for tag in ("wireframe_admin_uncovered", "wireframe_scrum_story_uncovered"):
        # appear at least twice (rule definition + whitelist)
        assert text.count(tag) >= 2, f"`{tag}` must appear in both rule def AND whitelist"


# ─── 5. spec-basic prompt drops 3-6 cap + mentions admin ─────────────────


def test_spec_basic_prompt_drops_3_6_cap_and_mentions_admin():
    text = (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")
    assert "3-6 entries" not in text, "prompt still has the arbitrary 3-6 cap"
    assert "後台" in text or "admin" in text.lower(), (
        "prompt must instruct AI to cover admin / 後台 UI surfaces"
    )


# ─── 6. spec-basic canonical example has admin wireframe ─────────────────


def test_spec_basic_canonical_has_admin_wireframe():
    ex = json.loads((TEMPLATES / "examples" / "spec-basic.input.json").read_text(encoding="utf-8"))
    wfs = ex.get("wireframes", [])
    has_admin = any(("後台" in w.get("name", "")) or ("admin" in w.get("name", "").lower())
                    for w in wfs)
    assert has_admin, (
        f"canonical wireframes must include an admin/後台 example; got names: "
        f"{[w.get('name') for w in wfs]}"
    )


# ─── 7-8. prototype admin coverage (cross_check) ─────────────────────────


def test_check_prototype_admin_coverage_flags_missing():
    from cross_check import check_prototype_admin_coverage
    sb = {"wireframes": [
        {"name": "玩家主畫面", "desc": "x"},
        {"name": "後台 — 玩家記錄列表", "desc": "y"},
    ]}
    proto = {"prototype_html": "<div class='phone'>only player UI</div>"}
    issues = check_prototype_admin_coverage(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_admin_uncovered" in cats


def test_check_prototype_admin_coverage_passes_when_present():
    from cross_check import check_prototype_admin_coverage
    sb = {"wireframes": [
        {"name": "玩家主畫面", "desc": "x"},
        {"name": "後台 — 玩家記錄列表", "desc": "y"},
    ]}
    # prototype_html mentions 後台 + has desktop-width marker
    proto = {"prototype_html":
             "<div class='phone'>player</div><div class='desktop' style='width:1200px'>後台玩家記錄</div>"}
    issues = check_prototype_admin_coverage(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_admin_uncovered" not in cats


# ─── 9. prototype review.md whitelist ────────────────────────────────────


def test_prototype_review_md_has_admin_rule():
    text = (TEMPLATES / "review" / "prototype.review.md").read_text(encoding="utf-8")
    assert text.count("prototype_admin_uncovered") >= 2, (
        "prototype_admin_uncovered must appear in rule def + whitelist"
    )


# ─── 10. prototype prompt allows desktop / admin ─────────────────────────


def test_prototype_prompt_drops_mobile_only_and_mentions_desktop():
    text = (TEMPLATES / "prompts" / "prototype.prompt.md").read_text(encoding="utf-8")
    # No hardcoded 375px viewport instruction
    assert "375px viewport" not in text, "prompt still hardcodes 375px viewport"
    assert "360px wide" not in text, "prompt still hardcodes 360px phone frame as the only allowed width"
    # Mentions desktop / admin / 後台 explicitly
    assert "desktop" in text.lower() or "桌面" in text, "prompt must mention desktop layout"
    assert "後台" in text or "admin" in text.lower(), "prompt must mention admin / 後台"


# ─── 11. prototype shell template not mobile-hardcoded ───────────────────


def test_prototype_shell_template_not_hardcoded_mobile_width():
    tpl = (TEMPLATES / "prototype.html.tmpl").read_text(encoding="utf-8")
    assert "width=375" not in tpl, "shell viewport must not hardcode width=375"
    assert "width=device-width" in tpl, "shell viewport must use device-width"


# ─── 12. prototype canonical includes admin demo ─────────────────────────


def test_prototype_canonical_has_admin_demo():
    ex = json.loads((TEMPLATES / "examples" / "prototype.input.json").read_text(encoding="utf-8"))
    html = ex.get("prototype_html", "")
    assert "後台" in html or "admin" in html.lower(), (
        "canonical prototype_html must show an admin / 後台 demo block"
    )
