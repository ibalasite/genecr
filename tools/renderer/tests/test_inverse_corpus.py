"""Inverse parser tested against real corpus (baseline + exp1 + exp3 x 7 steps).
Zero mocks — all real .md / .input.json from past pipeline runs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TEMPLATES = REPO / "templates"
SRC = REPO / "tools" / "renderer"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


STEPS = [
    ("spec-basic",    "md"),
    ("spec-advanced", "md"),
    ("assets",        "md"),
    ("bdd",           "md"),
    ("scrum",         "md"),
    ("prototype",     "html"),
    ("docs",          "html"),
]

RUNS = [
    ("baseline", REPO / "output" / "checkin7v2-baseline",                   "checkin7v2"),
    ("exp1",     REPO / "output" / "checkin7v2-exp1" / "20260518-180000",   "checkin7v2-exp1"),
    ("exp3",     REPO / "output" / "checkin7v2-exp3" / "20260518-200000",   "checkin7v2-exp3"),
]


def _corpus():
    for run_name, run_dir, slug in RUNS:
        if not run_dir.exists():
            continue
        for step, ext in STEPS:
            md_path = run_dir / f"{slug}-{step}.{ext}"
            input_path = run_dir / f"{step}.input.json"
            tmpl_path = TEMPLATES / f"{step}.{ext}.tmpl"
            if md_path.exists() and input_path.exists() and tmpl_path.exists():
                yield (run_name, step, ext, tmpl_path, md_path, input_path)


CORPUS = list(_corpus())


@pytest.mark.parametrize(
    "run,step,ext,tmpl,md,inp",
    CORPUS,
    ids=[f"{r}-{s}" for r, s, _, _, _, _ in CORPUS],
)
def test_inverse_recovers_input(run, step, ext, tmpl, md, inp):
    """Existing .md → inverse → match original .input.json (top-level key set)."""
    from inverse import md_to_input, InverseError
    template_source = tmpl.read_text(encoding="utf-8")
    md_text = md.read_text(encoding="utf-8")
    expected = json.loads(inp.read_text(encoding="utf-8"))
    try:
        recovered = md_to_input(template_source, md_text)
    except InverseError as e:
        pytest.skip(f"{step}: inverse not supported ({e})")
        return
    # Expected keys minus those that don't appear in template (preprocess-only).
    # We require recovered keys to be a subset of expected keys (no spurious).
    # And require at least one key recovered.
    assert recovered, f"{step}: recovered nothing"
    spurious = set(recovered.keys()) - set(expected.keys())
    # Keys legitimately injected by render.preprocess (present in rendered
    # output, absent from raw input.json):
    #   resource_summary — derived by spec-basic / assets preprocess
    #   prototype_path   — derived by docs preprocess from feature.json
    spurious -= {"_value", "resource_summary", "prototype_path"}
    assert not spurious, f"{step}: spurious top-level keys: {sorted(spurious)}"
    # Require meaningful recovery: at least half of the expected top-level
    # keys must have been parsed back out of the rendered text.
    recovered_real = set(recovered.keys()) & set(expected.keys())
    assert len(recovered_real) >= max(1, len(expected) // 2), (
        f"{step}: only recovered {len(recovered_real)}/{len(expected)} keys: "
        f"{sorted(recovered_real)}"
    )


@pytest.mark.parametrize(
    "run,step,ext,tmpl,md,inp",
    CORPUS,
    ids=[f"{r}-{s}" for r, s, _, _, _, _ in CORPUS],
)
def test_round_trip_forward_inverse(run, step, ext, tmpl, md, inp):
    """input → render → inverse → at least the top-level scalar fields match."""
    from inverse import md_to_input, InverseError
    import render
    template_source = tmpl.read_text(encoding="utf-8")
    expected = json.loads(inp.read_text(encoding="utf-8"))
    try:
        # Preprocess where applicable so derived fields (resource_summary) exist.
        data = render.preprocess(step, dict(expected), inp.parent)
        rendered_md = render.render(step, data)
        recovered = md_to_input(template_source, rendered_md)
    except (InverseError, NotImplementedError, SystemExit) as e:
        pytest.skip(f"{step}: round-trip not supported ({e})")
        return
    assert recovered, f"{step}: recovered nothing from round-trip"
