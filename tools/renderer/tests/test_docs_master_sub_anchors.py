"""Master/sub anchor namespacing in docs.html.

docs.html aggregates 7 sub-docs into one page. Each sub-doc is a "master page"
(spec-basic / spec-advanced / assets / bdd / scrum / api-explorer / prototype).
Anchors authored inside a sub-doc must be scoped to their master so they don't
collide globally (which previously caused: click sidebar 「API 試打」 → page
jumped to 技術版 because both had `<a id="api-checkin-config">`).

Convention:
  - master only:        `#spec-basic`
  - master + sub:       `#spec-advanced.api-checkin-config`
  - API explorer endpoint: `#api-explorer.api-checkin-config`
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def docs_template_src(repo_root) -> str:
    return (repo_root / "templates" / "docs.html.tmpl").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def spec_advanced_template_src(repo_root) -> str:
    return (repo_root / "templates" / "spec-advanced.md.tmpl").read_text(encoding="utf-8")


@pytest.fixture
def docs_rendered(render_module, repo_root, tmp_path) -> str:
    """Render docs with a minimal sections set so we can assert HTML output."""
    # Create stub sibling md files for each section
    (tmp_path / "feature.json").write_text('{"slug": "feat"}', encoding="utf-8")
    for t in ("spec-basic", "spec-advanced", "assets", "bdd", "scrum"):
        (tmp_path / f"feat-{t}.md").write_text(f"# {t}\n", encoding="utf-8")
    data = {
        "feature": {"name": "F", "slug": "feat"},
        "sections": [
            {"title": "📋 企畫版", "type": "spec-basic"},
            {"title": "⚙️ 技術版", "type": "spec-advanced"},
            {"title": "🎨 資源清單", "type": "assets"},
            {"title": "🧪 BDD", "type": "bdd"},
            {"title": "📌 SCRUM", "type": "scrum"},
        ],
        "api_explorer": [{"id": "api-foo", "method": "GET", "path": "/foo", "desc": "x", "responses": {}}],
        "prototype_path": "feat-prototype.html",
    }
    data = render_module.preprocess("docs", data, tmp_path)
    return render_module.render("docs", data)


# ─── A. Sidebar + master container naming ─────────────────────────────────


def test_sidebar_data_target_uses_master_names(docs_rendered):
    assert 'data-target="spec-basic"' in docs_rendered
    assert 'data-target="spec-advanced"' in docs_rendered
    assert 'data-target="assets"' in docs_rendered
    assert 'data-target="api-explorer"' in docs_rendered
    assert 'data-target="prototype"' in docs_rendered
    assert 'data-target="panel-0"' not in docs_rendered, "legacy numeric panel id leaked"
    assert 'data-target="panel-api"' not in docs_rendered, "legacy panel-api leaked"
    assert 'data-target="panel-proto"' not in docs_rendered, "legacy panel-proto leaked"


def test_master_containers_use_semantic_ids(docs_rendered):
    assert 'id="spec-basic"' in docs_rendered
    assert 'id="api-explorer"' in docs_rendered
    assert 'id="prototype"' in docs_rendered
    # No numeric/legacy panel ids
    assert 'id="panel-0"' not in docs_rendered
    assert 'id="panel-1"' not in docs_rendered
    assert 'id="panel-api"' not in docs_rendered
    assert 'id="panel-proto"' not in docs_rendered


# ─── B. Function naming reflects intent ───────────────────────────────────


def test_routing_function_named_for_intent(docs_template_src):
    """Routing function name should describe what it does, not be `_routeHash`."""
    assert "goToAnchor" in docs_template_src, "expected goToAnchor function"
    assert "_routeHash" not in docs_template_src, "legacy _routeHash name still present"


def test_mount_function_named_for_intent(docs_template_src):
    assert "mountSubDocIntoMaster" in docs_template_src, "expected mountSubDocIntoMaster function"
    assert "uniquifyHeadingIds" not in docs_template_src, "legacy uniquifyHeadingIds still present"


# ─── C. Routing rules in goToAnchor ───────────────────────────────────────


def test_routing_splits_on_dot_for_master_sub(docs_template_src):
    """goToAnchor must split target on first `.` — master vs master.sub."""
    fn_body = _extract_function(docs_template_src, "goToAnchor")
    assert "." in fn_body and ("split" in fn_body or "indexOf('.')" in fn_body), (
        "goToAnchor should split target on '.'"
    )


def test_routing_handles_api_explorer_master_with_sub(docs_template_src):
    """master == 'api-explorer' + sub → renderApi(sub) branch."""
    fn_body = _extract_function(docs_template_src, "goToAnchor")
    assert "api-explorer" in fn_body and "renderApi" in fn_body, (
        "goToAnchor should route api-explorer.<sub> to renderApi(sub)"
    )


def test_no_bare_name_fallback_to_global_dom(docs_template_src):
    """The old fallback `getElementById(target)` for an UNSCOPED (no dot) name
    caused the cross-master collision bug. After scoping, an id-lookup is only
    valid for a scoped `master.sub` target. The function MUST NOT have a path
    that, given a bare master-only or unknown target, walks the global DOM
    looking for any matching unscoped id.

    Concrete shape we forbid: a getElementById branch that runs when sub is
    empty / target has no dot. Acceptable: getElementById(target) called only
    inside a branch that already established target contains a dot (scoped).
    """
    fn_body = _extract_function(docs_template_src, "goToAnchor")
    # Require: there's a `if (!sub) return;` or equivalent guard so bare names
    # don't fall through to DOM scan. Heuristic: presence of `!sub` short-circuit
    # OR an explicit `dot === -1` guard returning before any element lookup.
    has_sub_guard = ("!sub" in fn_body or "sub === ''" in fn_body or
                     "sub == ''" in fn_body or "dot === -1" in fn_body)
    assert has_sub_guard, (
        "goToAnchor must short-circuit when target has no sub (bare master name) "
        "before attempting any global id lookup"
    )


# ─── D. spec-advanced cross-master links use master names ─────────────────


def test_widget_master_ids_not_prefixed_by_mounter(docs_template_src):
    """api-explorer / prototype panels are widget-only (no markdown sub-doc).
    JS references widget ids by short name (`getElementById('api-detail')`,
    `'api-resp-body'`, etc). mountSubDocIntoMaster MUST NOT prefix those —
    only `panel-doc` panels (which hold rendered markdown) get scoped.

    Forbidden: mounter walking every `.panel` indiscriminately.
    Required: mounter targets a narrower selector that excludes widget panels.
    """
    fn_body = _extract_function(docs_template_src, "mountSubDocIntoMaster")
    assert ".panel-doc" in fn_body or "panel-doc" in fn_body, (
        "mountSubDocIntoMaster must select only `.panel-doc` panels, not all `.panel`"
    )


def test_markdown_section_panels_have_panel_doc_class(docs_rendered):
    """Each rendered markdown section panel carries class `panel-doc` so the
    mounter knows it should be scoped."""
    # at least one markdown panel must carry the class
    assert 'class="panel panel-doc' in docs_rendered or \
           'class="panel active panel-doc' in docs_rendered, (
        "markdown section panels must carry `panel-doc` class"
    )


def test_widget_panels_do_not_have_panel_doc_class(docs_rendered):
    """api-explorer / prototype are widget panels — must NOT carry panel-doc
    class (which would cause runtime id prefixing of widget elements)."""
    import re
    m = re.search(r'<div class="panel[^"]*" id="api-explorer"', docs_rendered)
    assert m, "api-explorer container missing"
    assert "panel-doc" not in m.group(0), "api-explorer must not be panel-doc"

    m = re.search(r'<div class="panel[^"]*" id="prototype"', docs_rendered)
    assert m, "prototype container missing"
    assert "panel-doc" not in m.group(0), "prototype must not be panel-doc"


def test_spec_advanced_cross_master_links_use_master_names(spec_advanced_template_src):
    """spec-advanced template's '相關文件' section must link to master names,
    not legacy panel-N indices."""
    assert "(#spec-basic)" in spec_advanced_template_src
    assert "(#assets)" in spec_advanced_template_src
    assert "(#bdd)" in spec_advanced_template_src
    assert "(#scrum)" in spec_advanced_template_src
    assert "(#prototype)" in spec_advanced_template_src
    assert "(#panel-0)" not in spec_advanced_template_src
    assert "(#panel-proto)" not in spec_advanced_template_src


# ─── helper ───────────────────────────────────────────────────────────────


def _extract_function(src: str, name: str) -> str:
    """Crude extractor: from `function NAME(` to matching closing brace."""
    m = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", src)
    if not m:
        return ""
    start = m.end() - 1  # at the opening {
    depth = 0
    for i in range(start, len(src)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[start:i+1]
    return ""
