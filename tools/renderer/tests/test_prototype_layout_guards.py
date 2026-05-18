"""Five prototype layout/UX guards — pure text analysis, no browser, no IO.

Test layers:
A. Per-rule logic (positive + negative + boundary cases)
B. Step isolation (signature + downstream-ignore + runtime no disk IO)
C. Baseline + real-run validation
D. Three-layer sync (rule appears in prompt + review.md + cross_check)
"""
from __future__ import annotations
import inspect, sys, json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "tools" / "renderer"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

TEMPLATES = REPO / "templates"


def _wrap(html: str) -> dict:
    return {"feature": {"name":"f","slug":"f"}, "prototype_html": html}


# ─── A. Per-rule logic ──────────────────────────────────────────────────

# A1. horizontal_overflow
def test_overflow_fixed_px_exceeds_parent():
    from cross_check import check_proto_horizontal_overflow
    html = '<style>.phone{width:324px}.board{display:grid;grid-template-columns:repeat(2,1fr)}.cell{min-width:200px}</style><div class="phone"><div class="board"><div class="cell">A</div><div class="cell">B</div></div></div>'
    issues = check_proto_horizontal_overflow(_wrap(html))
    assert any(i.category == "prototype_horizontal_overflow" for i in issues)

def test_overflow_passes_when_flex_fr():
    from cross_check import check_proto_horizontal_overflow
    html = '<style>.phone{width:375px}.board{display:grid;grid-template-columns:repeat(7,minmax(0,1fr))}.cell{min-width:0}</style><div class="phone"><div class="board"><div class="cell">A</div></div></div>'
    assert check_proto_horizontal_overflow(_wrap(html)) == []

# A2. dead_nav_item
def test_dead_nav_opacity_low_no_handler():
    from cross_check import check_proto_dead_nav_item
    html = '<aside><a href="#a" onclick="goto(\'a\')">活躍</a><a style="opacity:.45;cursor:default">稽核日誌</a></aside>'
    issues = check_proto_dead_nav_item(_wrap(html))
    assert any(i.category == "prototype_dead_nav_item" and "稽核" in i.detail for i in issues)

def test_dead_nav_disabled_class():
    from cross_check import check_proto_dead_nav_item
    html = '<nav><a class="disabled">隱藏</a><a onclick="x()" data-page="a">顯示</a></nav>'
    issues = check_proto_dead_nav_item(_wrap(html))
    assert any(i.category == "prototype_dead_nav_item" for i in issues)

def test_nav_passes_when_all_functional():
    from cross_check import check_proto_dead_nav_item
    html = '<aside><a onclick="goto(\'a\')" data-page="a">A</a><a onclick="goto(\'b\')" data-page="b">B</a></aside><div data-pane="a">A</div><div data-pane="b">B</div>'
    assert check_proto_dead_nav_item(_wrap(html)) == []

# A3. button_no_handler
def test_button_no_handler_flagged():
    from cross_check import check_proto_button_no_handler
    html = '<button id="orphan">點我</button><script>console.log("hi")</script>'
    issues = check_proto_button_no_handler(_wrap(html))
    assert any(i.category == "prototype_button_no_handler" and "orphan" in i.detail for i in issues)

def test_button_with_onclick_passes():
    from cross_check import check_proto_button_no_handler
    assert check_proto_button_no_handler(_wrap('<button onclick="x()">A</button>')) == []

def test_button_with_listener_passes():
    from cross_check import check_proto_button_no_handler
    html = '<button id="ok">A</button><script>document.getElementById("ok").addEventListener("click", () => {})</script>'
    assert check_proto_button_no_handler(_wrap(html)) == []

def test_disabled_button_not_flagged():
    from cross_check import check_proto_button_no_handler
    assert check_proto_button_no_handler(_wrap('<button disabled>等待</button>')) == []

# A4. default_open_modal
def test_default_open_modal_flagged():
    from cross_check import check_proto_default_open_modal
    html = '<style>.help-modal{position:fixed;display:block;z-index:9999;top:20px;left:20px;width:400px}</style><div class="help-modal">說明</div>'
    issues = check_proto_default_open_modal(_wrap(html))
    assert any(i.category == "prototype_default_open_modal" for i in issues)

def test_hidden_modal_passes():
    from cross_check import check_proto_default_open_modal
    html = '<style>.help-modal{position:fixed;display:none;z-index:9999}</style><div class="help-modal">說明</div>'
    assert check_proto_default_open_modal(_wrap(html)) == []

# A5. admin_responsive_break
def test_admin_fixed_width_overflow_mobile_flagged():
    from cross_check import check_proto_admin_responsive_break
    html = '<style>.adm-form-grid{width:800px}</style><div class="adm-form-grid">form</div>'
    issues = check_proto_admin_responsive_break(_wrap(html))
    assert any(i.category == "prototype_admin_responsive_break" for i in issues)

def test_admin_with_media_guard_passes():
    from cross_check import check_proto_admin_responsive_break
    html = '<style>@media (min-width:768px){.adm-form-grid{width:800px}}</style>'
    assert check_proto_admin_responsive_break(_wrap(html)) == []


# ─── B. Step isolation ─────────────────────────────────────────────────

NEW_FNS = [
    "check_proto_horizontal_overflow",
    "check_proto_dead_nav_item",
    "check_proto_button_no_handler",
    "check_proto_default_open_modal",
    "check_proto_admin_responsive_break",
]
ALLOWED_PARAMS = {"prototype"}
FORBIDDEN_PARAMS = {"sa","sb","sb_data","assets","scrum","bdd","docs","path","base_dir","run_dir","file_path","input_path"}

@pytest.mark.parametrize("name", NEW_FNS)
def test_signature_only_takes_prototype(name):
    import cross_check
    fn = getattr(cross_check, name)
    sig = inspect.signature(fn)
    param_names = [p.name for p in sig.parameters.values()]
    assert param_names == ["prototype"], f"{name} must take only 'prototype', got {param_names}"

@pytest.mark.parametrize("name", NEW_FNS)
def test_no_disk_io(monkeypatch, name):
    import builtins
    real = builtins.open
    def guard(file, *a, **kw):
        s = str(file)
        if ".input.json" in s and "tests" not in s:
            raise AssertionError(f"{name} attempted sibling read: {s}")
        return real(file, *a, **kw)
    monkeypatch.setattr(builtins, "open", guard)
    import cross_check
    fn = getattr(cross_check, name)
    _ = fn(_wrap('<button>x</button><style>.a{width:10px}</style>'))  # must not raise

def test_run_all_checks_does_not_pass_downstream_to_proto_helpers():
    """Even if upstream_dict accidentally contains bdd/scrum/docs, proto helpers
    should not see them — orchestrator only feeds depends_on chain."""
    from cross_check import run_all_checks
    sb = {"feature":{"name":"f","slug":"f"},"wireframes":[]}
    proto = {"feature":{"name":"f","slug":"f"}, "prototype_html":'<button onclick="x()">A</button>'}
    # Clean upstream
    clean = run_all_checks("prototype", {"spec-basic":sb, "prototype":proto})
    # With pollution (downstream keys present)
    polluted = run_all_checks("prototype", {"spec-basic":sb, "prototype":proto,
                                             "bdd":{"junk":True},"scrum":{"junk":True},"docs":{"junk":True}})
    # Result must be identical regardless of downstream presence
    assert [(i.category, i.detail) for i in clean] == [(i.category, i.detail) for i in polluted]


# ─── C. Baseline + real-run validation ─────────────────────────────────

def _load_proto(run: str) -> dict:
    return json.loads((REPO / "output" / run / "prototype.input.json").read_text(encoding="utf-8"))

def test_baseline_passes_all_new_proto_rules():
    """Baseline prototype is canonical — must pass all 5 new checks."""
    from cross_check import (check_proto_horizontal_overflow, check_proto_dead_nav_item,
                              check_proto_button_no_handler, check_proto_default_open_modal,
                              check_proto_admin_responsive_break)
    proto = _load_proto("checkin7v2-baseline")
    for fn in [check_proto_horizontal_overflow, check_proto_dead_nav_item,
               check_proto_button_no_handler, check_proto_default_open_modal,
               check_proto_admin_responsive_break]:
        issues = fn(proto)
        assert issues == [], f"baseline must pass {fn.__name__}; got: {[(i.category, i.detail[:80]) for i in issues]}"

def test_exp1_horizontal_overflow_caught():
    """exp1 prototype has the cells-overflow-phone bug; must be caught."""
    from cross_check import check_proto_horizontal_overflow
    proto = _load_proto("checkin7v2-exp1/20260518-180000")
    issues = check_proto_horizontal_overflow(proto)
    assert any(i.category == "prototype_horizontal_overflow" for i in issues), \
        f"exp1 overflow not caught: {[(i.category, i.detail[:80]) for i in issues]}"

def test_exp1_dead_nav_caught():
    """exp1 has <a opacity:.45 cursor:default>稽核日誌</a> dead nav."""
    from cross_check import check_proto_dead_nav_item
    proto = _load_proto("checkin7v2-exp1/20260518-180000")
    issues = check_proto_dead_nav_item(proto)
    assert any("稽核" in i.detail for i in issues), \
        f"exp1 dead 稽核日誌 nav not caught: {[(i.category, i.detail[:80]) for i in issues]}"


# ─── D. Three-layer sync ───────────────────────────────────────────────

NEW_CATEGORIES = [
    "prototype_horizontal_overflow",
    "prototype_dead_nav_item",
    "prototype_button_no_handler",
    "prototype_default_open_modal",
    "prototype_admin_responsive_break",
]

@pytest.mark.parametrize("cat", NEW_CATEGORIES)
def test_category_in_review_md(cat):
    text = (TEMPLATES / "review" / "prototype.review.md").read_text(encoding="utf-8")
    assert text.count(cat) >= 2, f"{cat} must appear in rule def + whitelist of review.md"

@pytest.mark.parametrize("cat", NEW_CATEGORIES)
def test_category_implemented_in_cross_check(cat):
    src = (SRC / "cross_check.py").read_text(encoding="utf-8")
    assert cat in src, f"{cat} must be implemented in cross_check.py"

def test_prompt_mentions_layout_safety():
    text = (TEMPLATES / "prompts" / "prototype.prompt.md").read_text(encoding="utf-8")
    assert "Layout safety" in text or "layout safety" in text.lower(), \
        "prompt must have a layout safety section"
