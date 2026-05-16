"""pipeline.json must declare the confirmed dependency chain.

If an upstream step's output is missing, execute_one's unmet check
naturally blocks downstream — no GUI status hack needed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

EXPECTED = {
    "spec-basic":    [],
    "spec-advanced": ["spec-basic"],
    "assets":        ["spec-basic"],
    "bdd":           ["spec-basic", "spec-advanced", "assets"],
    "scrum":         ["spec-basic", "spec-advanced", "assets"],
    "prototype":     ["spec-basic", "spec-advanced", "assets"],
    "docs":          ["spec-basic", "spec-advanced", "assets",
                      "bdd", "scrum", "prototype"],
}


@pytest.fixture(scope="module")
def pipeline_cfg():
    return json.loads((REPO_ROOT / "pipeline.json").read_text(encoding="utf-8"))


def test_pipeline_has_all_seven_steps(pipeline_cfg):
    names = [s["name"] for s in pipeline_cfg["steps"]]
    assert set(names) == set(EXPECTED.keys())


@pytest.mark.parametrize("step,expected_deps", list(EXPECTED.items()))
def test_step_dependencies_match(pipeline_cfg, step, expected_deps):
    s = next(x for x in pipeline_cfg["steps"] if x["name"] == step)
    deps = s.get("depends_on", [])
    assert sorted(deps) == sorted(expected_deps), (
        f"{step} depends_on mismatch:\n  expected: {expected_deps}\n  got: {deps}"
    )


def test_no_step_depends_on_self(pipeline_cfg):
    for s in pipeline_cfg["steps"]:
        deps = s.get("depends_on", [])
        assert s["name"] not in deps, f"{s['name']} depends on itself"


def test_all_dependencies_reference_existing_steps(pipeline_cfg):
    names = {s["name"] for s in pipeline_cfg["steps"]}
    for s in pipeline_cfg["steps"]:
        for d in s.get("depends_on", []):
            assert d in names, f"{s['name']} depends on unknown step '{d}'"


def test_dependency_graph_is_acyclic(pipeline_cfg):
    """Topological sort must succeed — no cycles."""
    deps = {s["name"]: list(s.get("depends_on", [])) for s in pipeline_cfg["steps"]}
    ordered: list[str] = []
    while deps:
        ready = [n for n, ds in deps.items() if not ds]
        assert ready, f"cycle detected in remaining: {deps}"
        for n in ready:
            ordered.append(n)
            del deps[n]
        for ds in deps.values():
            ds[:] = [d for d in ds if d not in ordered]
