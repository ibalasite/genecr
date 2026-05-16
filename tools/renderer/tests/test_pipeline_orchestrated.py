"""Smoke tests for the pipeline ↔ review_loop adapter.

Verifies the wiring without actually shelling out to AI: we patch subprocess
to record what would have been called, and check that the role prompts get
substituted correctly.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline_orchestrated import (
    _build_schema_validator,
    _format_role_prompt,
    _load_all_upstream,
    make_subprocess_invoker,
    orchestrated_call_ai_for_step,
)


def test_load_upstream_collects_input_json_files(tmp_path):
    (tmp_path / "spec-basic.input.json").write_text(
        json.dumps({"x": 1}), encoding="utf-8"
    )
    (tmp_path / "assets.input.json").write_text(
        json.dumps({"y": 2}), encoding="utf-8"
    )
    (tmp_path / "noise.txt").write_text("not me", encoding="utf-8")

    data = _load_all_upstream("bdd", tmp_path)
    assert data == {"spec-basic": {"x": 1}, "assets": {"y": 2}}


def test_schema_validator_returns_strings_on_error():
    validate = _build_schema_validator("spec-basic")
    errors = validate({"bad": True})  # missing all required fields
    assert errors, "expected validation errors"
    assert all(isinstance(e, str) for e in errors)


def test_schema_validator_passes_valid_example():
    """spec-basic schema validates against its own example."""
    repo = Path(__file__).resolve().parents[3]
    example = json.loads(
        (repo / "templates" / "examples" / "spec-basic.input.json").read_text(encoding="utf-8")
    )
    validate = _build_schema_validator("spec-basic")
    assert validate(example) == []


def test_format_generator_prompt_includes_brief(tmp_path):
    brief = tmp_path / "brief.txt"
    brief.write_text("BUILD A BINGO GAME", encoding="utf-8")
    out = _format_role_prompt("generator", "spec-basic", {"upstream": {}}, brief)
    assert "BUILD A BINGO GAME" in out


def test_format_reviewer_prompt_includes_step_rules(tmp_path):
    out = _format_role_prompt("reviewer", "bdd", {
        "input": {"scenarios": []},
        "upstream": {"spec-basic": {}},
    }, tmp_path / "brief.txt")
    assert "INDEPENDENT REVIEWER" in out
    # Step-specific review rules embedded
    assert "sequenceDiagram" in out  # bdd.review.md mentions it


def test_format_fixer_prompt_includes_issues(tmp_path):
    out = _format_role_prompt("fixer", "assets", {
        "input": {"assets": []},
        "issues": [{"step": "assets", "category": "x", "detail": "off by one"}],
        "upstream": {"spec-basic": {"x": 1}},
    }, tmp_path / "brief.txt")
    assert "off by one" in out
    assert "INDEPENDENT FIXER" in out


def test_subprocess_invoker_writes_prompt_and_reads_output(tmp_path, monkeypatch):
    """When subprocess produces an output file, invoker returns its contents."""
    def fake_run(cmd, **kwargs):
        # Parse {output} path from cmd
        # cmd format: "fake {prompt} > {output}" — extract last token
        out_path = Path(cmd.split(">")[-1].strip())
        out_path.write_text('{"feature": {"name": "x", "slug": "x"}}',
                            encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    brief = tmp_path / "brief.txt"
    brief.write_text("brief", encoding="utf-8")
    invoker = make_subprocess_invoker(
        ai_command="fake {prompt} > {output}",
        step_type="spec-basic",
        brief_file=brief,
        work_dir=tmp_path,
    )
    out = invoker("generator", {"upstream": {}})
    assert "feature" in out
    # Combined prompt file should have been written
    combined = list(tmp_path.glob("*.combined.prompt.md"))
    assert combined, "combined prompt file not written"


def test_orchestrated_call_writes_input_json_on_success(tmp_path, monkeypatch):
    """End-to-end smoke: mocked AI returns the real example (already proven
    to validate against schema) for generator; reviewer returns empty
    issues. Final input.json gets written."""
    repo = Path(__file__).resolve().parents[3]
    valid = json.loads(
        (repo / "templates" / "examples" / "spec-basic.input.json").read_text(encoding="utf-8")
    )

    def fake_run(cmd, **kwargs):
        out_path = Path(cmd.split(">")[-1].strip())
        path_str = str(out_path)
        if "generator" in path_str or "fixer" in path_str:
            out_path.write_text(json.dumps(valid), encoding="utf-8")
        else:  # reviewer
            out_path.write_text(json.dumps({"issues": []}), encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    brief = tmp_path / "brief.txt"
    brief.write_text("brief", encoding="utf-8")
    result = orchestrated_call_ai_for_step(
        step_name="spec-basic",
        step_type="spec-basic",
        ai_cfg={"command": "fake {prompt} > {output}"},
        brief_file=brief,
        run_dir=tmp_path,
    )
    assert result.success, f"unexpected: {result.final_issues}"
    final_json = tmp_path / "spec-basic.input.json"
    assert final_json.exists()
    data = json.loads(final_json.read_text(encoding="utf-8"))
    assert "feature" in data
