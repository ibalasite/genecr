"""Step isolation gate — render.py and cross_check.py must NEVER read sibling files.
Three layers: source grep + runtime mock + signature inspection."""
from __future__ import annotations

import inspect
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_RENDERER = REPO_ROOT / "tools" / "renderer"

# Sibling-step file name suffix that step preprocess must never read.
_SIBLING_INPUT_SUFFIX = ".input" + ".json"  # avoid literal-token tripping our own grep


# ─── Layer 1: source grep ───────────────────────────────────────────────


def test_cross_check_source_has_no_disk_io():
    src = (SRC_RENDERER / "cross_check.py").read_text(encoding="utf-8")
    forbidden = ["open(", "Path(", ".glob(", ".exists()", ".read_text(", "json.load(", "pathlib", _SIBLING_INPUT_SUFFIX]
    for token in forbidden:
        assert token not in src, f"cross_check.py contains forbidden disk-IO token: {token!r}"


def test_render_source_only_docs_branch_reads_disk():
    """render.py may only read disk inside the docs aggregator branch."""
    src = (SRC_RENDERER / "render.py").read_text(encoding="utf-8")
    # No sibling input.json reads anywhere (docs reads .md and feature.json, not sibling step files).
    assert _SIBLING_INPUT_SUFFIX not in src, "render.py must not reference sibling step input files"
    # _compute_resource_summary must be deleted.
    assert "_compute_resource_summary" not in src, "anti-pattern function still present"


# ─── Layer 2: runtime mock ──────────────────────────────────────────────


def _install_input_guard(monkeypatch):
    import builtins
    real_open = builtins.open

    def guard(file, *a, **kw):
        s = str(file)
        if _SIBLING_INPUT_SUFFIX in s and "tests" not in s:
            raise AssertionError(f"render preprocess attempted sibling read: {s}")
        return real_open(file, *a, **kw)

    monkeypatch.setattr(builtins, "open", guard)


def test_preprocess_spec_basic_no_disk(monkeypatch, tmp_path):
    _install_input_guard(monkeypatch)
    import sys
    if str(SRC_RENDERER) not in sys.path:
        sys.path.insert(0, str(SRC_RENDERER))
    import render
    sb = {
        "feature": {"name": "f", "slug": "f"},
        "resource_counts": {
            "visual_total": 10,
            "audio_total": 3,
            "image": {"a": 1},
            "animation": {"b": 1},
            "sound": {"c": 1},
            "particle": {"d": 1},
            "modules": 1,
            "acceptance_criteria": 1,
            "api_endpoints": 1,
        },
    }
    out = render.preprocess("spec-basic", dict(sb), tmp_path)
    assert out["resource_summary"]["visual_total"] == 10
    assert out["resource_summary"]["audio_total"] == 3
    assert out["resource_summary"]["total"] == 13


def test_preprocess_assets_no_disk(monkeypatch, tmp_path):
    _install_input_guard(monkeypatch)
    import sys
    if str(SRC_RENDERER) not in sys.path:
        sys.path.insert(0, str(SRC_RENDERER))
    import render
    a = {
        "feature": {"name": "f", "slug": "f"},
        "assets": [
            {"id": "A1", "type": "image", "name": "x", "category": "c",
             "owner_role": "art", "output_format": "PNG", "suggested_filename": "x.png", "usage": "u" * 25},
            {"id": "A2", "type": "sound", "name": "y", "category": "c",
             "owner_role": "art", "output_format": "WAV", "suggested_filename": "y.wav", "usage": "u" * 25},
        ],
    }
    out = render.preprocess("assets", dict(a), tmp_path)
    assert out["resource_summary"]["image"] == 1
    assert out["resource_summary"]["sound"] == 1
    assert out["resource_summary"]["visual_total"] == 1
    assert out["resource_summary"]["audio_total"] == 1
    assert out["resource_summary"]["total"] == 2


# ─── Layer 3: signature inspection ──────────────────────────────────────


def test_cross_check_functions_no_path_params():
    import sys
    if str(SRC_RENDERER) not in sys.path:
        sys.path.insert(0, str(SRC_RENDERER))
    import cross_check
    bad = {"base_dir", "run_dir", "path", "file_path", "input_path"}
    for name, fn in inspect.getmembers(cross_check, inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.name not in bad, f"cross_check.{name}: forbidden path param {p.name!r}"
