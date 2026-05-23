from __future__ import annotations

import json
from pathlib import Path

from ai_command import format_ai_command, resolve_ai_command


def test_pipeline_json_declares_copilot_command(repo_root: Path):
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    assert pipeline["ai"]["commands"]["copilot"] == "copilot -s < {prompt} > {output}"


def test_resolve_ai_command_picks_copilot_from_pipeline_map(monkeypatch, repo_root: Path):
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    monkeypatch.setenv("GENECR_HOST", "copilot")
    assert resolve_ai_command(pipeline["ai"]) == "copilot -s < {prompt} > {output}"


def test_format_ai_command_for_copilot_uses_prompt_and_output_paths(tmp_path: Path):
    prompt_path = tmp_path / "prompt.md"
    output_path = tmp_path / "out.txt"
    command = format_ai_command(
        "copilot -s < {prompt} > {output}",
        prompt_path=prompt_path,
        output_path=output_path,
    )
    assert str(prompt_path) in command
    assert str(output_path) in command
