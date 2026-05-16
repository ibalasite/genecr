"""Every step must have a JSON schema, and its example must validate.

After this commit all 7 steps have schemas — closes the 5/7 gap where
spec-advanced / assets / bdd / scrum / docs were running without any
validation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = REPO_ROOT / "templates" / "schemas"
EXAMPLES = REPO_ROOT / "templates" / "examples"

ALL_STEPS = [
    "spec-basic",
    "spec-advanced",
    "assets",
    "bdd",
    "scrum",
    "prototype",
    "docs",
]


@pytest.mark.parametrize("step", ALL_STEPS)
def test_schema_file_exists(step):
    p = SCHEMAS / f"{step}.schema.json"
    assert p.exists(), f"missing schema: {p}"


@pytest.mark.parametrize("step", ALL_STEPS)
def test_schema_is_valid_jsonschema(step):
    schema = json.loads((SCHEMAS / f"{step}.schema.json").read_text(encoding="utf-8"))
    Draft7Validator.check_schema(schema)


@pytest.mark.parametrize("step", ALL_STEPS)
def test_example_validates_against_schema(step):
    schema = json.loads((SCHEMAS / f"{step}.schema.json").read_text(encoding="utf-8"))
    example = json.loads((EXAMPLES / f"{step}.input.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(example), key=lambda e: e.path)
    assert not errors, (
        f"{step} example fails schema:\n"
        + "\n".join(
            f"  at {'.'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
            for e in errors
        )
    )


def test_bdd_schema_enforces_sequence_diagram_required():
    """User-flagged: bdd scenarios must always have sequence_diagram.
    Schema must enforce this (otherwise refactor could silently drop it)."""
    schema = json.loads((SCHEMAS / "bdd.schema.json").read_text(encoding="utf-8"))
    scenario_required = schema["properties"]["scenarios"]["items"]["required"]
    assert "sequence_diagram" in scenario_required


def test_spec_advanced_schema_enforces_architecture_diagram_required():
    """Mermaid architecture diagram is a preserved render feature — required."""
    schema = json.loads((SCHEMAS / "spec-advanced.schema.json").read_text(encoding="utf-8"))
    arch_required = schema["properties"]["architecture"]["required"]
    assert "diagram" in arch_required
