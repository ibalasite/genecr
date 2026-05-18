"""prototype layout skeleton + walkthrough step coverage守門.

Past bugs (admin regen):
- AI 自己刻 tabs + surface 切換 → layout broken (tabs/手機偏右、cell 不見、admin tab 切不過去)
- 玩家旅程「下一步」從多步壓成 2 步 (AI 把「至少 3 步」當上限以騰位置給 admin)

修法：固定 layout skeleton (AI 只填 surface 內容，不刻 tab 結構)，
程式驗 proto-help 步數必須等於 user_journey + admin_journey 全部 1:1。
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


# ─── A. cross_check.check_prototype_layout_skeleton ──────────────────────


def test_check_layout_flags_missing_proto_page():
    from cross_check import check_prototype_layout_skeleton
    sb = {"wireframes": [{"name": "後台 — x", "html": "<div>"}]}
    proto = {"prototype_html": "<div class='wrap'>no skeleton</div>"}
    issues = check_prototype_layout_skeleton(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_layout_skeleton_missing" in cats


def test_check_layout_passes_with_skeleton():
    from cross_check import check_prototype_layout_skeleton
    sb = {"wireframes": [{"name": "後台 — x", "html": "<div>"}]}
    html = (
        '<div class="proto-page">'
        '  <div class="proto-tabs"><button class="proto-tab on" data-surface="player">玩家端</button>'
        '   <button class="proto-tab" data-surface="admin">管理後台</button></div>'
        '  <div class="proto-surface on" data-surface="player">玩家手機 demo content</div>'
        '  <div class="proto-surface" data-surface="admin">後台桌面 demo content</div>'
        '  <div class="proto-help"><ol><li>step1</li></ol></div>'
        '</div>'
    )
    proto = {"prototype_html": html}
    issues = check_prototype_layout_skeleton(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_layout_skeleton_missing" not in cats


def test_check_layout_flags_admin_surface_empty():
    from cross_check import check_prototype_layout_skeleton
    sb = {"wireframes": [{"name": "後台 — 玩家記錄", "html": "<div>"}]}
    # admin surface declared but completely empty
    html = (
        '<div class="proto-page">'
        '  <div class="proto-tabs"></div>'
        '  <div class="proto-surface on" data-surface="player">player</div>'
        '  <div class="proto-surface" data-surface="admin"></div>'
        '</div>'
    )
    proto = {"prototype_html": html}
    issues = check_prototype_layout_skeleton(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_admin_surface_empty" in cats


# ─── B. cross_check.check_prototype_help_step_coverage ───────────────────


def test_check_help_steps_flags_too_few():
    """user_journey 7 + admin_journey 3 = 10 expected, only 4 in help → fail."""
    from cross_check import check_prototype_help_step_coverage
    sb = {
        "user_journey": [{"action": f"u{i}"} for i in range(7)],
        "admin_journey": [{"action": f"a{i}"} for i in range(3)],
        "wireframes": [],
    }
    proto = {"prototype_html":
             '<div class="proto-help"><ol>'
             '<li>1</li><li>2</li><li>3</li><li>4</li>'
             '</ol></div>'}
    issues = check_prototype_help_step_coverage(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_help_steps_incomplete" in cats
    # Detail must say expected vs got
    detail = next(i.detail for i in issues if i.category == "prototype_help_steps_incomplete")
    assert "10" in detail and "4" in detail


def test_check_help_steps_passes_when_full_coverage():
    from cross_check import check_prototype_help_step_coverage
    sb = {
        "user_journey": [{"action": f"u{i}"} for i in range(3)],
        "admin_journey": [{"action": f"a{i}"} for i in range(2)],
        "wireframes": [],
    }
    items = ''.join(f'<li>step{i}</li>' for i in range(5))
    proto = {"prototype_html": f'<div class="proto-help"><ol>{items}</ol></div>'}
    issues = check_prototype_help_step_coverage(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_help_steps_incomplete" not in cats


def test_check_help_steps_falls_back_to_admin_wireframes_count():
    """若 spec-basic 沒 admin_journey 但有 admin wireframes，
    用 admin wireframes 數量補位（不准跳過）。"""
    from cross_check import check_prototype_help_step_coverage
    sb = {
        "user_journey": [{"action": "u1"}, {"action": "u2"}],
        "wireframes": [
            {"name": "玩家 — x"},
            {"name": "後台 — a"},
            {"name": "後台 — b"},
        ],
    }
    # expected = 2 (user_journey) + 2 (admin wireframes) = 4
    items = ''.join(f'<li>step{i}</li>' for i in range(3))  # only 3
    proto = {"prototype_html": f'<div class="proto-help"><ol>{items}</ol></div>'}
    issues = check_prototype_help_step_coverage(sb, proto)
    cats = {i.category for i in issues}
    assert "prototype_help_steps_incomplete" in cats


# ─── C. prototype.prompt locks skeleton + step formula ───────────────────


@pytest.fixture(scope="module")
def prototype_prompt_src() -> str:
    return (TEMPLATES / "prompts" / "prototype.prompt.md").read_text(encoding="utf-8")


def test_prototype_prompt_has_skeleton_template(prototype_prompt_src):
    text = prototype_prompt_src
    assert "proto-page" in text and "proto-surface" in text and "proto-tabs" in text, (
        "prompt must provide a fixed layout skeleton (proto-page / proto-tabs / proto-surface)"
    )


def test_prototype_prompt_locks_step_formula(prototype_prompt_src):
    text = prototype_prompt_src
    # Must reference both journeys + state 1:1 coverage
    assert "user_journey" in text and "admin_journey" in text
    assert "1:1" in text or "1對1" in text or "len(" in text, (
        "prompt must state proto-help step count == len(user_journey) + len(admin_journey)"
    )


# ─── D. prototype shell template has skeleton CSS ────────────────────────


@pytest.fixture(scope="module")
def prototype_shell_src() -> str:
    return (TEMPLATES / "prototype.html.tmpl").read_text(encoding="utf-8")


def test_prototype_shell_has_skeleton_css(prototype_shell_src):
    text = prototype_shell_src
    assert ".proto-page" in text and ".proto-surface" in text and ".proto-tabs" in text, (
        "prototype shell must include CSS for proto-page / proto-tabs / proto-surface"
    )


# ─── E. prototype.review.md has layout rules ─────────────────────────────


@pytest.fixture(scope="module")
def prototype_review_src() -> str:
    return (TEMPLATES / "review" / "prototype.review.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("tag", [
    "prototype_layout_skeleton_missing",
    "prototype_admin_surface_empty",
    "prototype_help_steps_incomplete",
])
def test_prototype_review_has_layout_rule(prototype_review_src, tag):
    assert prototype_review_src.count(tag) >= 2, (
        f"prototype review.md must have `{tag}` in rule def + whitelist"
    )


# ─── F. prototype canonical uses skeleton ────────────────────────────────


def test_prototype_canonical_uses_skeleton():
    ex = json.loads((TEMPLATES / "examples" / "prototype.input.json").read_text(encoding="utf-8"))
    html = ex.get("prototype_html", "")
    assert "proto-page" in html and "proto-surface" in html and "proto-tabs" in html, (
        "canonical prototype_html must use proto-page / proto-tabs / proto-surface skeleton"
    )
    # Both surfaces present
    assert 'data-surface="player"' in html and 'data-surface="admin"' in html
