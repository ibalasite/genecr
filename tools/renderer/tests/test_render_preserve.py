"""Baseline preservation tests.

These assertions document the special blocks each step currently produces.
They must remain GREEN both before AND after the architecture refactor —
optimization must not silently delete existing functionality (mermaid
diagrams, wireframe embeds, API tables, etc.).

If a refactor needs to remove a marker, that's a conscious decision: update
this test AND notify the user, do not silently delete.
"""
from __future__ import annotations

from pathlib import Path

import pytest


# ─── spec-basic ────────────────────────────────────────────────────────────

def test_spec_basic_renders(render_module, spec_basic_example):
    md = render_module.render("spec-basic", spec_basic_example)
    assert md, "spec-basic render returned empty"
    assert len(md) > 500, f"spec-basic render too short ({len(md)} bytes)"


def test_spec_basic_has_wireframe_html(render_module, spec_basic_example):
    """Wireframes embed pre-built HTML via Jinja `| safe`."""
    md = render_module.render("spec-basic", spec_basic_example)
    assert "線框圖" in md or "wireframe" in md.lower(), "wireframe section heading missing"


def test_spec_basic_has_competitor_table(render_module, spec_basic_example):
    md = render_module.render("spec-basic", spec_basic_example)
    # Markdown table rows: pipe-separated; competitor section emits 我們 column
    assert "| 我們" in md or "我們 |" in md, "competitor comparison column missing"


def test_spec_basic_has_matrix_or_i18n_table(render_module, spec_basic_example):
    md = render_module.render("spec-basic", spec_basic_example)
    # At least one markdown table separator must exist
    assert "|---" in md or "| ---" in md or "|--" in md, "no markdown tables rendered"


# ─── spec-advanced ─────────────────────────────────────────────────────────

def test_spec_advanced_renders(render_module, spec_advanced_example):
    md = render_module.render("spec-advanced", spec_advanced_example)
    assert md and len(md) > 500


def test_spec_advanced_has_architecture_mermaid(render_module, spec_advanced_example):
    """architecture.diagram must render as a mermaid code block."""
    md = render_module.render("spec-advanced", spec_advanced_example)
    assert "```mermaid" in md, "architecture mermaid block missing"


def test_spec_advanced_has_api_table(render_module, spec_advanced_example):
    md = render_module.render("spec-advanced", spec_advanced_example)
    # API section uses Method column
    assert "Method" in md or "method" in md.lower(), "API table missing"


# ─── assets ────────────────────────────────────────────────────────────────

def test_assets_renders(render_module, assets_example):
    md = render_module.render("assets", assets_example)
    assert md and len(md) > 100


# ─── bdd ───────────────────────────────────────────────────────────────────

def test_bdd_renders(render_module, bdd_example):
    md = render_module.render("bdd", bdd_example)
    assert md and len(md) > 200


def test_bdd_has_sequence_diagram_per_scenario(render_module, bdd_example):
    """User-flagged critical feature: every scenario must render a mermaid
    sequenceDiagram block. Optimization must preserve this."""
    md = render_module.render("bdd", bdd_example)
    scenarios = bdd_example.get("scenarios", [])
    assert scenarios, "bdd example has no scenarios"
    sd_count = md.count("sequenceDiagram")
    assert sd_count >= len(scenarios), (
        f"expected sequenceDiagram block per scenario "
        f"({len(scenarios)}); found {sd_count}"
    )


def test_bdd_has_gherkin_code_blocks(render_module, bdd_example):
    md = render_module.render("bdd", bdd_example)
    # Gherkin blocks are typically fenced; at minimum the keywords appear
    assert "Given" in md or "Scenario" in md or "假設" in md or "情境" in md, (
        "no Gherkin keywords rendered"
    )


# ─── scrum ─────────────────────────────────────────────────────────────────

def test_scrum_renders(render_module, scrum_example):
    md = render_module.render("scrum", scrum_example)
    assert md and len(md) > 200


# ─── prototype ─────────────────────────────────────────────────────────────

def test_prototype_renders_html(render_module, prototype_example):
    html = render_module.render("prototype", prototype_example)
    assert html and "<html" in html.lower(), "prototype output is not HTML"


def test_prototype_has_viewport_and_dark_bg(render_module, prototype_example):
    html = render_module.render("prototype", prototype_example)
    assert "viewport" in html, "viewport meta missing"
    # Dark background per template (#0a0a14)
    assert "#0a0a14" in html or "background" in html.lower(), (
        "dark background style missing"
    )


def test_prototype_embeds_ai_html(render_module, prototype_example):
    """prototype_html field must be embedded via `| safe` (not escaped)."""
    html = render_module.render("prototype", prototype_example)
    proto_html = prototype_example.get("prototype_html", "")
    if proto_html:
        # Should appear unescaped; if escaped we'd see &lt; instead of <
        first_tag = proto_html.split(">", 1)[0]
        if "<" in first_tag:
            assert first_tag in html, "prototype_html was escaped, not embedded raw"


# ─── docs ──────────────────────────────────────────────────────────────────
# docs.render() requires sibling .md files via preprocess; skip live render
# and instead assert template-level features exist in the HTML template.

def test_docs_template_has_mermaid(repo_root):
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    assert "mermaid" in tpl.lower(), "docs template missing mermaid"


def test_docs_template_has_api_config(repo_root):
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    assert "API_CONFIG" in tpl, "docs template missing API_CONFIG (API Explorer)"


def test_docs_template_has_lightbox(repo_root):
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    assert "lightbox" in tpl.lower(), "docs template missing lightbox"


def test_docs_template_has_sidebar(repo_root):
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    assert "sidebar" in tpl.lower(), "docs template missing sidebar"


def test_docs_template_has_complete_wireframe_css(repo_root):
    """Every wf-* class the DSL declares must have a CSS rule in
    docs.html.tmpl. AI uses these classes; missing CSS = layout collapses.
    """
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    required_classes = [
        # Containers
        ".wf-scope", ".wf-frame", ".wf-panel", ".wf-mobile", ".wf-desktop",
        ".wf-statusbar", ".wf-appbar", ".wf-banner", ".wf-marquee",
        ".wf-stage", ".wf-info", ".wf-actionbar", ".wf-shortcuts",
        ".wf-bottomnav", ".wf-sidebar", ".wf-sidenav-item",
        ".wf-modal", ".wf-modal-icon", ".wf-modal-title", ".wf-modal-body",
        ".wf-modal-meta", ".wf-modal-actions", ".wf-empty",
        # 排版 / 列表 / 文字
        ".wf-row", ".wf-list", ".wf-line", ".wf-text", ".wf-link",
        ".wf-table", ".wf-tr", ".wf-td",
        ".wf-section-title", ".wf-helper", ".wf-divider",
        # Form
        ".wf-input", ".wf-input-date", ".wf-select", ".wf-textarea",
        ".wf-check", ".wf-radio", ".wf-switch",
        # 按鈕/標籤/角標
        ".wf-btn", ".wf-btn-primary", ".wf-pill", ".wf-badge", ".wf-dot",
        ".wf-required", ".wf-countdown", ".wf-icon-slot",
        # 進階
        ".wf-tabs", ".wf-tab", ".wf-accordion", ".wf-stepper", ".wf-step",
        ".wf-toast",
        # 進度/圖表/載入
        ".wf-skeleton-line", ".wf-skeleton-pill", ".wf-skeleton-block",
        ".wf-bar", ".wf-chart", ".wf-chart-bars", ".wf-kpi", ".wf-kpi-grid",
        ".wf-card", ".wf-list-line", ".wf-line-row", ".wf-segment",
        # 輪盤
        ".wf-wheel", ".wf-wheel-pointer", ".wf-wheel-hub", ".wf-wheel-rim",
        ".wf-board",
    ]
    missing = [c for c in required_classes if c not in tpl]
    assert not missing, (
        f"docs.html.tmpl missing CSS for: {missing}\n"
        f"AI uses these classes; without CSS the layout collapses."
    )


def test_wireframe_styleguide_renders_all_primitives(repo_root):
    """Living style guide must demo every DSL primitive (so AI/dev have
    a visual reference to copy from)."""
    sg = (repo_root / "templates" / "wireframe-styleguide.html").read_text(encoding="utf-8")
    must_demo = [
        "wf-row", "wf-list", "wf-line", "wf-text", "wf-link",
        "wf-table", "wf-tr", "wf-td",
        "wf-input", "wf-input-date", "wf-select", "wf-textarea",
        "wf-check", "wf-radio", "wf-switch",
        "wf-btn", "wf-pill", "wf-badge", "wf-dot",
        "wf-tabs", "wf-tab", "wf-stepper", "wf-step",
        "wf-accordion", "wf-toast",
        "wf-skeleton-pill", "wf-skeleton-line", "wf-skeleton-block",
        "wf-bar", "wf-chart", "wf-kpi", "wf-kpi-grid",
        "wf-mobile", "wf-stage", "wf-board", "wf-actionbar",
        "wf-desktop", "wf-sidebar", "wf-sidenav-item",
        "wf-modal", "wf-modal-title",
    ]
    missing = [c for c in must_demo if c not in sg]
    assert not missing, f"styleguide missing demo for: {missing}"


def test_wireframe_containers_have_max_width(repo_root):
    """All wireframe containers MUST have a bounded width (sandbox principle).
    wireframes represent screens, never page-spanning responsive layout."""
    tpl = (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")
    # Each container's CSS rule should contain a width constraint
    for cls, must in [
        (".wf-mobile", "width: 360px"),
        (".wf-modal {", "width: 300px"),
        (".wf-frame", "max-width: 720px"),
        (".wf-desktop", "max-width: 960px"),
    ]:
        # find the rule and check it contains the constraint within ~300 chars
        i = tpl.find(cls)
        assert i >= 0, f"{cls} rule missing from docs.html.tmpl"
        rule_body = tpl[i:i+400]
        assert must in rule_body, f"{cls} missing constraint '{must}' — wireframe will overflow page width"


def test_wireframe_dsl_doc_lists_all_primitives(repo_root):
    """wireframe-dsl.md must register every primitive in section 3 tables."""
    dsl = (repo_root / "templates" / "wireframe-dsl.md").read_text(encoding="utf-8")
    must_register = [
        ".wf-row", ".wf-list", ".wf-line", ".wf-text", ".wf-link",
        ".wf-table", ".wf-input", ".wf-select", ".wf-check", ".wf-radio",
        ".wf-switch", ".wf-tabs", ".wf-stepper", ".wf-toast", ".wf-kpi",
        ".wf-bar", ".wf-desktop", ".wf-sidebar",
    ]
    missing = [c for c in must_register if c not in dsl]
    assert not missing, f"wireframe-dsl.md missing primitive: {missing}"


# ─── Jinja `| safe` filter preservation ────────────────────────────────────

@pytest.mark.parametrize("tmpl_name", [
    "spec-basic.md.tmpl",
    "prototype.html.tmpl",
    "docs.html.tmpl",
])
def test_jinja_safe_filter_preserved(repo_root, tmpl_name):
    """| safe filter must remain in templates that embed raw HTML — removing
    it breaks wireframe / mermaid / interactive HTML embeds."""
    tpl_path = repo_root / "templates" / tmpl_name
    if not tpl_path.exists():
        pytest.skip(f"{tmpl_name} not present")
    content = tpl_path.read_text(encoding="utf-8")
    assert "| safe" in content, f"{tmpl_name} lost `| safe` filter"
