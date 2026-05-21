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


# ── data_models: conditional required by kind (closes convergence bug) ──

_SA_SHELL = {
    "feature": {"name": "x", "slug": "x"},
    "architecture": {"overview": "o", "diagram": "graph TD\n  A-->B"},
    "client": {"scene": "s", "components": [], "states": []},
    "apis": [{
        "id": "a1", "method": "GET", "path": "/x",
        "summary": "get x", "description": "get x detail",
        "auth": {"required": False, "type": "none"}, "parameters": [],
        "responses": {
            "200": {"description": "ok", "schema": {}, "example": {}},
            "400": {"description": "bad request", "schema": {}, "example": {}},
        },
    }],
    "data_models": [],
    "business_logic": [{"title": "t", "desc": "d"}],
    "cache_strategy": [],
}


def _validate_sa(data):
    schema = json.loads((SCHEMAS / "spec-advanced.schema.json").read_text(encoding="utf-8"))
    return list(Draft7Validator(schema).iter_errors(data))


def test_redis_string_key_passes_without_fields():
    """The exact case that infinite-looped in run1: redis string key,
    AI sensibly omits fields. Must now pass schema."""
    data = {**_SA_SHELL, "data_models": [
        {
            "name": "checkin_daily_lock",
            "kind": "redis",
            "redis_pattern": "checkin:lock:{player_id}:{yyyymmdd}",
            "value_type": "string",
            "ttl": 86400,
            # NO fields[]
        }
    ]}
    errs = _validate_sa(data)
    assert errs == [], f"redis string key without fields should pass, got: {[e.message for e in errs]}"


def test_redis_without_pattern_or_value_type_fails():
    data = {**_SA_SHELL, "data_models": [
        {"name": "cache", "kind": "redis"}  # missing both required redis fields
    ]}
    errs = _validate_sa(data)
    assert errs, "redis entry without pattern/value_type should fail"


def test_mysql_without_fields_fails():
    data = {**_SA_SHELL, "data_models": [
        {"name": "users", "kind": "mysql"}  # missing fields[]
    ]}
    errs = _validate_sa(data)
    assert errs, "mysql entry without fields should fail"


def test_mysql_with_fields_passes():
    data = {**_SA_SHELL, "data_models": [
        {
            "name": "users", "kind": "mysql",
            "fields": [{"name": "uid", "type": "BIGINT"}],
        }
    ]}
    assert _validate_sa(data) == []


def test_mysql_table_string_kind_also_treated_as_relational():
    """AI sometimes uses 'MySQL Table' (with space) as kind — treat as
    non-redis → require fields[]."""
    data_no_fields = {**_SA_SHELL, "data_models": [
        {"name": "users", "kind": "MySQL Table"}
    ]}
    assert _validate_sa(data_no_fields), "'MySQL Table' without fields must fail"

    data_with_fields = {**_SA_SHELL, "data_models": [
        {"name": "users", "kind": "MySQL Table",
         "fields": [{"name": "uid", "type": "BIGINT"}]}
    ]}
    assert _validate_sa(data_with_fields) == []
