"""Admin wireframe MUST use desktop DSL primitives, not mobile/loading ones.

Past bug: AI generated admin wireframes using `wf-frame` (narrow mobile-ish
container) + `wf-skeleton-pill` (shimmer loading placeholder) as form inputs
+ rows of `wf-pill` (small badges) faking table cells. Rendered admin pages
looked like cramped mobile forms with pill rows instead of proper desktop
form + table layouts.

This file guards the four-layer fix:
  - DSL CSS has desktop primitives (topbar / toolbar / main / form-row /
    pagination / stat-card / etc) on par with mobile
  - wireframe-dsl.md documents them + admin quick-pick reference
  - spec-basic prompt has admin DSL hard rules (DO / DON'T)
  - spec-basic review.md + cross_check enforce them
  - canonical admin wireframes use the desktop primitives
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


# ─── A. DSL CSS — desktop primitives on par with mobile ──────────────────


REQUIRED_DESKTOP_CSS_CLASSES = [
    ".wf-desktop",           # 容器（單面）
    ".wf-desktop-app",       # 容器（含 sidebar）
    ".wf-topbar",            # 頂部 header
    ".wf-main",              # 主內容區
    ".wf-toolbar",           # 表格上方搜尋/篩選/動作列
    ".wf-breadcrumb",        # 麵包屑
    ".wf-pagination",        # 分頁器
    ".wf-form-row",          # label + input 對
    ".wf-form-grid",         # 多欄表單
    ".wf-stat-card",         # KPI 卡
    ".wf-cards-grid",        # 卡片網格
]


@pytest.fixture(scope="module")
def docs_template_src() -> str:
    return (TEMPLATES / "docs.html.tmpl").read_text(encoding="utf-8")


@pytest.mark.parametrize("css_class", REQUIRED_DESKTOP_CSS_CLASSES)
def test_docs_template_has_desktop_css_primitive(docs_template_src, css_class):
    assert css_class in docs_template_src, (
        f"docs.html.tmpl missing CSS for {css_class} — desktop DSL not on par with mobile"
    )


def test_wf_desktop_is_not_forced_sidebar_grid(docs_template_src):
    """Old wf-desktop hardcoded `grid-template-columns: 240px 1fr` — forces
    sidebar. Single-pane admin breaks. wf-desktop now should be flex column
    (no sidebar); wf-desktop-app is the variant with sidebar."""
    # Crude: find wf-desktop rule, ensure it does NOT contain a hardcoded
    # grid-template-columns with two columns.
    import re
    m = re.search(r"\.wf-desktop\s*\{([^}]+)\}", docs_template_src)
    assert m, "wf-desktop rule not found"
    body = m.group(1)
    assert "grid-template-columns" not in body, (
        "wf-desktop must not hardcode grid-template-columns (use wf-desktop-app for sidebar layout)"
    )


# ─── B. wireframe-dsl.md documents desktop primitives ────────────────────


@pytest.fixture(scope="module")
def dsl_md_src() -> str:
    return (TEMPLATES / "wireframe-dsl.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("primitive", [
    "wf-topbar", "wf-main", "wf-toolbar", "wf-breadcrumb",
    "wf-pagination", "wf-form-row", "wf-form-grid", "wf-stat-card",
    "wf-cards-grid", "wf-desktop-app",
])
def test_dsl_md_documents_desktop_primitive(dsl_md_src, primitive):
    assert primitive in dsl_md_src, f"wireframe-dsl.md missing entry for `{primitive}`"


def test_dsl_md_has_admin_quick_pick_section(dsl_md_src):
    """Quick reference for admin wireframe authors — what classes to pick."""
    assert "後台" in dsl_md_src and ("速查" in dsl_md_src or "quick" in dsl_md_src.lower()), (
        "wireframe-dsl.md must have an admin quick-pick / 速查 section"
    )


# ─── C. spec-basic prompt has admin DSL hard rules ───────────────────────


@pytest.fixture(scope="module")
def spec_basic_prompt_src() -> str:
    return (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")


def test_spec_basic_prompt_bans_wf_frame_for_admin(spec_basic_prompt_src):
    text = spec_basic_prompt_src
    # The prompt must say wf-frame is forbidden for admin OR require wf-desktop
    assert "wf-frame" in text and ("禁" in text or "❌" in text), (
        "prompt must explicitly forbid wf-frame for admin wireframes"
    )


def test_spec_basic_prompt_requires_wf_input_for_admin_form(spec_basic_prompt_src):
    text = spec_basic_prompt_src
    assert "wf-input" in text, "prompt must mention wf-input as the admin form input"
    assert "wf-skeleton-pill" in text and ("禁" in text or "❌" in text), (
        "prompt must explicitly forbid wf-skeleton-pill as form input (it's a loading placeholder)"
    )


def test_spec_basic_prompt_requires_wf_table_for_admin_table(spec_basic_prompt_src):
    text = spec_basic_prompt_src
    assert "wf-table" in text, "prompt must mention wf-table for tabular admin data"


# ─── D. spec-basic review.md has R16-R18 ─────────────────────────────────


@pytest.fixture(scope="module")
def spec_basic_review_src() -> str:
    return (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("tag", [
    "admin_wireframe_wrong_container",
    "admin_form_uses_skeleton_pill",
    "admin_table_uses_pills",
])
def test_spec_basic_review_has_admin_dsl_rule(spec_basic_review_src, tag):
    assert spec_basic_review_src.count(tag) >= 2, (
        f"review.md must have `{tag}` in both rule def and whitelist"
    )


# ─── E. cross_check.check_admin_wireframe_dsl ────────────────────────────


def test_check_admin_wireframe_flags_wf_frame():
    from cross_check import check_admin_wireframe_dsl
    sb = {"wireframes": [
        {"name": "後台 — 活動設定",
         "html": '<div class="wf-scope"><div class="wf-frame"><input class="wf-input"></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    cats = {i.category for i in issues}
    assert "admin_wireframe_wrong_container" in cats


def test_check_admin_wireframe_passes_with_wf_desktop():
    from cross_check import check_admin_wireframe_dsl
    sb = {"wireframes": [
        {"name": "後台 — 活動設定",
         "html": '<div class="wf-scope"><div class="wf-desktop"><input class="wf-input"></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    cats = {i.category for i in issues}
    assert "admin_wireframe_wrong_container" not in cats


def test_check_admin_wireframe_flags_skeleton_pill():
    from cross_check import check_admin_wireframe_dsl
    sb = {"wireframes": [
        {"name": "後台 — 活動設定",
         "html": '<div class="wf-scope"><div class="wf-desktop"><div class="wf-skeleton-pill"></div></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    cats = {i.category for i in issues}
    assert "admin_form_uses_skeleton_pill" in cats


def test_check_admin_wireframe_flags_fake_table_from_pills():
    from cross_check import check_admin_wireframe_dsl
    pills = ''.join('<span class="wf-pill">x</span>' for _ in range(5))
    sb = {"wireframes": [
        {"name": "後台 — 玩家記錄",
         "html": f'<div class="wf-scope"><div class="wf-desktop"><div class="wf-row">{pills}</div></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    cats = {i.category for i in issues}
    assert "admin_table_uses_pills" in cats


def test_check_admin_wireframe_passes_with_proper_table():
    from cross_check import check_admin_wireframe_dsl
    sb = {"wireframes": [
        {"name": "後台 — 玩家記錄",
         "html": '<div class="wf-scope"><div class="wf-desktop">'
                 '<div class="wf-table"><div class="wf-tr">'
                 '<div class="wf-td">玩家</div><div class="wf-td">天數</div>'
                 '</div></div></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    cats = {i.category for i in issues}
    assert "admin_table_uses_pills" not in cats
    assert "admin_wireframe_wrong_container" not in cats


def test_check_admin_wireframe_ignores_player_wireframes():
    """Player-facing wireframes are free to use wf-frame / wf-skeleton-pill / wf-pill
    (mobile primitives) — only admin wireframes get checked."""
    from cross_check import check_admin_wireframe_dsl
    sb = {"wireframes": [
        {"name": "玩家 — 主畫面",
         "html": '<div class="wf-frame"><div class="wf-skeleton-pill"></div></div>'}
    ]}
    issues = check_admin_wireframe_dsl(sb)
    assert not issues


# ─── F. canonical admin wireframes use desktop primitives ────────────────


def test_canonical_admin_wireframe_uses_desktop_primitives():
    ex = json.loads((TEMPLATES / "examples" / "spec-basic.input.json").read_text(encoding="utf-8"))
    admin_wfs = [w for w in ex.get("wireframes", [])
                 if "後台" in w.get("name", "") or "admin" in w.get("name", "").lower()]
    assert len(admin_wfs) >= 2, "canonical needs ≥ 2 admin wireframes as examples"
    for w in admin_wfs:
        html = w.get("html", "")
        # MUST use wf-desktop (not wf-frame)
        assert "wf-desktop" in html, (
            f"canonical admin wireframe '{w['name']}' must use wf-desktop container"
        )
        assert 'class="wf-frame"' not in html, (
            f"canonical admin wireframe '{w['name']}' must not use wf-frame"
        )
        # MUST NOT use wf-skeleton-pill (loading placeholder)
        assert "wf-skeleton-pill" not in html, (
            f"canonical admin wireframe '{w['name']}' must not use wf-skeleton-pill"
        )


def test_canonical_admin_form_uses_wf_input():
    """The 活動設定 canonical must show wf-input usage."""
    ex = json.loads((TEMPLATES / "examples" / "spec-basic.input.json").read_text(encoding="utf-8"))
    form_wfs = [w for w in ex.get("wireframes", []) if "設定" in w.get("name", "")]
    assert form_wfs, "canonical needs an admin 設定/form wireframe"
    for w in form_wfs:
        assert "wf-input" in w["html"], (
            f"admin form wireframe '{w['name']}' must show wf-input usage"
        )


def test_canonical_admin_table_uses_wf_table():
    """The 玩家記錄 canonical must show wf-table > wf-tr > wf-td."""
    ex = json.loads((TEMPLATES / "examples" / "spec-basic.input.json").read_text(encoding="utf-8"))
    list_wfs = [w for w in ex.get("wireframes", []) if "記錄" in w.get("name", "") or "列表" in w.get("name", "")]
    assert list_wfs, "canonical needs an admin list/records wireframe"
    for w in list_wfs:
        html = w["html"]
        assert "wf-table" in html and "wf-tr" in html and "wf-td" in html, (
            f"admin list wireframe '{w['name']}' must use wf-table > wf-tr > wf-td"
        )
