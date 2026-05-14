"""
Headless test for genecr-gui — exercises pure helpers without opening Tk.

Run: python C:/Projects/genecr/gui/test_headless.py
"""
import sys
import importlib.util
from pathlib import Path

# Load .pyw as a module
spec = importlib.util.spec_from_file_location("g", str(Path(__file__).with_name("genecr-gui.pyw")))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_helpers():
    print("─── helper functions ───")
    print(f"  detect_genecr_dir() = {g.detect_genecr_dir()}")
    print(f"  default_outdir()    = {g.default_outdir()}")
    print(f"  find_python()       = {g.find_python()}")
    gd = g.detect_genecr_dir()
    if gd:
        print(f"  detect_host(gd)     = {g.detect_host(gd)}")
        print(f"  pipeline_json       = {gd / 'pipeline.json'}")
    assert gd is not None and gd.exists(), "genecr install not detected"
    print("  ✅ helpers OK\n")


def test_parse_pipeline_line():
    print("─── parse_pipeline_line ───")
    cases = [
        ("▶ spec-basic: AI step",                 ("start", "spec-basic")),
        ("   ✓ spec-basic: format OK on attempt 1", ("done", "spec-basic")),
        ("   [render] spec-basic → foo-spec-basic.md", ("render_done", "spec-basic")),
        ("Run: C:\\foo\\bar\\baz",                ("run_dir", "C:\\foo\\bar\\baz")),
        ("random log line",                       None),
    ]
    for line, expected in cases:
        got = g.parse_pipeline_line(line)
        ok = "✅" if got == expected else "❌"
        print(f"  {ok}  {line!r}\n      got={got}  expected={expected}")
        assert got == expected, f"mismatch on {line!r}"
    print("  ✅ all cases pass\n")


def test_extract_slug_name():
    print("─── extract_slug_name (real Gemini call) ───")
    brief = "做一個中秋節限定活動，玩家可以收集月餅碎片合成完整月餅換獎"
    data, err = g.extract_slug_name(brief, "gemini", timeout=60)
    if err:
        print(f"  ❌ error: {err}")
        return False
    print(f"  ✅ data = {data}")
    assert "slug" in data and "name" in data
    assert data["slug"], "slug empty"
    assert data["name"], "name empty"
    return True


if __name__ == "__main__":
    test_helpers()
    test_parse_pipeline_line()
    test_extract_slug_name()
    print("\n✅ all headless tests passed")
