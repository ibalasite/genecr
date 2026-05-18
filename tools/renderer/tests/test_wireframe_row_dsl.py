"""wf-row may only contain inline DSL primitives directly. Block primitives
(wf-panel, wf-card, wf-board, wf-banner, wf-table, etc.) inside wf-row overflow
the mobile/desktop frame width — flag as wireframe_row_contains_block.

This is a COMMON rule, not feature-specific."""
from __future__ import annotations
import inspect, pathlib, sys, json
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
TEMPLATES = REPO_ROOT / "templates"
SRC = REPO_ROOT / "tools" / "renderer"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _wf(html: str) -> dict:
    return {"feature":{"name":"f","slug":"f"}, "wireframes":[{"name":"W","desc":"d","html":html}]}


# ─── A. Logic correctness ────────────────────────────────────────────────

def test_inline_only_row_passes():
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-scope"><div class="wf-mobile"><div class="wf-row"><span class="wf-pill">D1</span><span class="wf-pill">D2</span><span class="wf-pill">D3</span></div></div></div>')
    assert check_wireframe_row_inline_only(sb) == []


def test_block_panel_in_row_flagged():
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-row"><div class="wf-panel">D1</div><span class="wf-pill">D2</span></div>')
    issues = check_wireframe_row_inline_only(sb)
    cats = {i.category for i in issues}
    assert "wireframe_row_contains_block" in cats
    assert any("wf-panel" in i.detail for i in issues)


def test_multiple_blocks_in_row_all_flagged():
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-row"><div class="wf-panel">A</div><div class="wf-card">B</div><div class="wf-board">C</div></div>')
    issues = check_wireframe_row_inline_only(sb)
    # All three offending children flagged (count >= 3)
    assert len(issues) >= 3


def test_block_outside_row_passes():
    """wf-stage > wf-panel (block in non-row container) is fine."""
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-stage"><div class="wf-panel">A</div><div class="wf-panel">B</div></div>')
    assert check_wireframe_row_inline_only(sb) == []


def test_nested_row_inside_panel_panel_not_in_row_passes():
    """Panel containing rows is the normal pattern."""
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-panel"><div class="wf-row"><span class="wf-pill">a</span></div></div>')
    assert check_wireframe_row_inline_only(sb) == []


def test_baseline_wireframes_pass():
    from cross_check import check_wireframe_row_inline_only
    sb = json.loads((REPO_ROOT / "output" / "checkin7v2-baseline" / "spec-basic.input.json").read_text(encoding="utf-8"))
    issues = check_wireframe_row_inline_only(sb)
    assert issues == [], f"baseline must pass; got: {[i.detail for i in issues]}"


def test_exp3_main_screen_flagged():
    """exp3 main screen used wf-panel children in wf-row — must be caught."""
    from cross_check import check_wireframe_row_inline_only
    sb = json.loads((REPO_ROOT / "output" / "checkin7v2-exp3" / "20260518-200000" / "spec-basic.input.json").read_text(encoding="utf-8"))
    issues = check_wireframe_row_inline_only(sb)
    cats = {i.category for i in issues}
    assert "wireframe_row_contains_block" in cats
    # Must flag the main screen wireframe specifically
    assert any("活動主畫面" in i.detail or "主畫面" in i.detail for i in issues)


# ─── B. Step isolation ───────────────────────────────────────────────────

def test_signature_only_takes_sb():
    from cross_check import check_wireframe_row_inline_only
    sig = inspect.signature(check_wireframe_row_inline_only)
    names = list(sig.parameters.keys())
    assert names == ["spec_basic"], f"must take only spec_basic, got {names}"
    forbidden = {"sa","sb_data","assets","scrum","bdd","path","base_dir","run_dir","file_path"}
    for p in sig.parameters.values():
        assert p.name not in forbidden, f"forbidden param: {p.name}"


def test_no_disk_io_at_runtime(monkeypatch):
    """Mock open: function must not trigger any *.input.json read."""
    import builtins
    real_open = builtins.open
    def guard(file, *a, **kw):
        s = str(file)
        if ".input.json" in s and "tests" not in s:
            raise AssertionError(f"check_wireframe_row_inline_only attempted sibling read: {s}")
        return real_open(file, *a, **kw)
    monkeypatch.setattr(builtins, "open", guard)
    from cross_check import check_wireframe_row_inline_only
    sb = _wf('<div class="wf-row"><span class="wf-pill">a</span></div>')
    _ = check_wireframe_row_inline_only(sb)  # must not raise


# ─── C. Three-layer sync ─────────────────────────────────────────────────

def test_rule_documented_in_prompt():
    text = (TEMPLATES / "prompts" / "spec-basic.prompt.md").read_text(encoding="utf-8")
    assert "wf-row" in text, "prompt must reference wf-row rule"
    assert "inline" in text.lower(), "prompt must mention inline constraint"


def test_rule_documented_in_review():
    text = (TEMPLATES / "review" / "spec-basic.review.md").read_text(encoding="utf-8")
    assert text.count("wireframe_row_contains_block") >= 2, (
        "wireframe_row_contains_block must appear in rule def + whitelist"
    )


def test_rule_implemented_in_cross_check():
    src = (SRC / "cross_check.py").read_text(encoding="utf-8")
    assert "def check_wireframe_row_inline_only" in src
    # Wired into run_all_checks for spec-basic
    assert "check_wireframe_row_inline_only(sb)" in src


def test_run_all_checks_invokes_for_spec_basic():
    from cross_check import run_all_checks
    sb = _wf('<div class="wf-row"><div class="wf-panel">x</div></div>')
    issues = run_all_checks("spec-basic", {"spec-basic": sb})
    cats = {i.category for i in issues}
    assert "wireframe_row_contains_block" in cats
