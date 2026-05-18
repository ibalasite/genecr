"""Render-based prototype layout audit. Uses Playwright if available;
gracefully skips when not. Catches browser-actual overflow bugs that
static text analysis misses (grid 1fr + aspect-ratio without min-width:0).
"""
from __future__ import annotations
import inspect, sys, json, importlib
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "tools" / "renderer"
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))


def _wrap(html: str) -> dict:
    return {"feature":{"name":"f","slug":"f"}, "prototype_html": html}


# ─── A. Graceful degradation ──────────────────────────────────────────

def test_skips_silently_when_playwright_missing(monkeypatch, capsys):
    """If playwright unimportable, returns [] + stderr warning, no exception."""
    import cross_check
    real_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__
    def fake_import(name, *a, **kw):
        if name == "playwright.sync_api" or name == "playwright":
            raise ImportError("playwright not installed")
        return real_import(name, *a, **kw)
    monkeypatch.setattr("builtins.__import__", fake_import)
    cross_check._PLAYWRIGHT_WARNED = False
    issues = cross_check.check_proto_layout_via_browser(_wrap('<div>hello</div>'))
    assert issues == []
    err = capsys.readouterr().err
    assert "playwright not installed" in err
    assert "playwright install chromium" in err

def test_skips_silently_when_chromium_launch_fails(monkeypatch, capsys):
    """If chromium binary missing, returns [] + stderr warning."""
    import cross_check
    try:
        import playwright.sync_api  # noqa
    except ImportError:
        pytest.skip("playwright not installed; mock-launch test n/a")
    class _FakeBrowser:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def chromium(self):
            class _Launcher:
                def launch(self, **kw): raise RuntimeError("Executable doesn't exist")
            return _Launcher()
    def fake_sp(): return _FakeBrowser()
    monkeypatch.setattr("playwright.sync_api.sync_playwright", fake_sp)
    issues = cross_check.check_proto_layout_via_browser(_wrap('<div>x</div>'))
    assert issues == []
    err = capsys.readouterr().err
    assert "SKIPPED" in err or "skipped" in err.lower()


# ─── B. Step isolation ───────────────────────────────────────────────

def test_signature_only_takes_prototype():
    import cross_check
    sig = inspect.signature(cross_check.check_proto_layout_via_browser)
    names = list(sig.parameters.keys())
    assert names == ["prototype"], f"must take only 'prototype', got {names}"

def test_no_disk_io_at_runtime(monkeypatch):
    """Must not open any .input.json file even when playwright present."""
    import builtins
    real = builtins.open
    def guard(file, *a, **kw):
        s = str(file)
        if ".input.json" in s and "tests" not in s:
            raise AssertionError(f"layout check attempted sibling read: {s}")
        return real(file, *a, **kw)
    monkeypatch.setattr(builtins, "open", guard)
    import cross_check
    _ = cross_check.check_proto_layout_via_browser(_wrap('<button>x</button>'))


# ─── C. Real rendering (needs playwright) ─────────────────────────────

def _has_playwright_chromium():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
            return True
    except Exception:
        return False

skip_no_browser = pytest.mark.skipif(not _has_playwright_chromium(), reason="playwright chromium not available")

@skip_no_browser
def test_simple_no_overflow_passes():
    from cross_check import check_proto_layout_via_browser
    html = '<html><body><div style="width:300px;height:100px">x</div></body></html>'
    assert check_proto_layout_via_browser(_wrap(html)) == []

@skip_no_browser
def test_overflow_detected():
    from cross_check import check_proto_layout_via_browser
    html = '''<html><body>
      <div style="width:300px;overflow-x:hidden">
        <div style="display:flex">
          <div style="width:200px;flex-shrink:0">A</div>
          <div style="width:200px;flex-shrink:0">B</div>
        </div>
      </div>
    </body></html>'''
    issues = check_proto_layout_via_browser(_wrap(html))
    assert any(i.category == "prototype_browser_overflow" for i in issues)
    assert any("CLIPPED" in i.detail for i in issues)

@skip_no_browser
def test_baseline_prototype_passes():
    """Baseline must produce no browser-detected overflow."""
    from cross_check import check_proto_layout_via_browser
    proto = json.loads((REPO / "output" / "checkin7v2-baseline" / "prototype.input.json").read_text(encoding="utf-8"))
    issues = check_proto_layout_via_browser(proto)
    assert issues == [], f"baseline must pass browser layout audit; got:\n" + "\n".join(i.detail for i in issues[:5])

@skip_no_browser
def test_exp1_cells_overflow_caught():
    """exp1 prototype's .phone (324px) is overflowed by .board (~462px) in
    checkin scene — the user's original reported bug. Must be caught."""
    from cross_check import check_proto_layout_via_browser
    proto = json.loads((REPO / "output" / "checkin7v2-exp1" / "20260518-180000" / "prototype.input.json").read_text(encoding="utf-8"))
    issues = check_proto_layout_via_browser(proto)
    assert any(i.category == "prototype_browser_overflow" for i in issues), \
        f"exp1 prototype overflow not caught; got {len(issues)} issues"
    assert any("phone" in i.detail.lower() and "CLIPPED" in i.detail for i in issues), \
        f"phone-clipped overflow not specifically caught; details: {[i.detail[:100] for i in issues[:5]]}"


# ─── D. Three-layer sync ─────────────────────────────────────────────

def test_category_in_review_md():
    text = (REPO / "templates" / "review" / "prototype.review.md").read_text(encoding="utf-8")
    assert text.count("prototype_browser_overflow") >= 2, "must appear in rule + whitelist"

def test_category_implemented_in_cross_check():
    src = (SRC / "cross_check.py").read_text(encoding="utf-8")
    assert "check_proto_layout_via_browser" in src
    assert "prototype_browser_overflow" in src

def test_grid_item_min_width_advice_in_prompt():
    text = (REPO / "templates" / "prompts" / "prototype.prompt.md").read_text(encoding="utf-8")
    assert "aspect-ratio" in text.lower(), "prompt must mention aspect-ratio sizing rule"
    assert "min-width" in text.lower(), "prompt must mention min-width: 0 requirement"
