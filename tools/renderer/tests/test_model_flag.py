from __future__ import annotations

from pathlib import Path

from ai_command import format_ai_command, resolve_ai_command


# ── resolve_ai_command: model_flag 注入 ──────────────────────────────────────

def test_resolve_injects_model_flag_when_models_configured(monkeypatch):
    """有 models.<host> 時，resolve 後的指令含 --model <id>。"""
    monkeypatch.setenv("GENECR_HOST", "claude")
    ai_cfg = {
        "commands": {"claude": "claude -p {model_flag} < {prompt} > {output}"},
        "models":   {"claude": "claude-haiku-4-5-20251001"},
    }
    cmd = resolve_ai_command(ai_cfg)
    assert "--model claude-haiku-4-5-20251001" in cmd


def test_resolve_model_flag_empty_when_no_models_key(monkeypatch):
    """沒有 models 欄位時，{model_flag} 為空字串，指令不含 --model。"""
    monkeypatch.setenv("GENECR_HOST", "claude")
    ai_cfg = {
        "commands": {"claude": "claude -p {model_flag} < {prompt} > {output}"},
    }
    cmd = resolve_ai_command(ai_cfg)
    assert "--model" not in cmd
    assert "{model_flag}" not in cmd


def test_resolve_model_flag_empty_when_host_not_in_models(monkeypatch):
    """models 有其他 host，但沒有當前 host，{model_flag} 為空字串。"""
    monkeypatch.setenv("GENECR_HOST", "gemini")
    ai_cfg = {
        "commands": {"gemini": "gemini {model_flag} < {prompt} > {output}"},
        "models":   {"claude": "claude-haiku-4-5-20251001"},
    }
    cmd = resolve_ai_command(ai_cfg)
    assert "--model" not in cmd
    assert "{model_flag}" not in cmd


# ── format_ai_command: {model_flag} 替換 ────────────────────────────────────

def test_format_replaces_model_flag_with_value(tmp_path: Path):
    """{model_flag} 被正確替換成 --model <id>。"""
    cmd = format_ai_command(
        "claude -p {model_flag} < {prompt} > {output}",
        prompt_path=tmp_path / "p.md",
        output_path=tmp_path / "o.txt",
        model_flag="--model claude-haiku-4-5-20251001",
    )
    assert "--model claude-haiku-4-5-20251001" in cmd


def test_format_replaces_model_flag_with_empty(tmp_path: Path):
    """{model_flag} 為空字串時，指令不含 --model。"""
    cmd = format_ai_command(
        "claude -p {model_flag} < {prompt} > {output}",
        prompt_path=tmp_path / "p.md",
        output_path=tmp_path / "o.txt",
        model_flag="",
    )
    assert "--model" not in cmd
    assert "{model_flag}" not in cmd


# ── pipeline.json 結構驗證 ───────────────────────────────────────────────────

def test_pipeline_json_has_models_for_all_hosts(repo_root: Path):
    """pipeline.json ai.models 必須有四個 host 的 model 設定。"""
    import json
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    models = pipeline["ai"]["models"]
    for host in ("claude", "codex", "gemini", "copilot"):
        assert host in models, f"ai.models.{host} 缺失"
        assert models[host], f"ai.models.{host} 不可為空"


def test_pipeline_json_commands_contain_model_flag(repo_root: Path):
    """pipeline.json ai.commands 每個 host 的指令必須含 {model_flag}。"""
    import json
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    commands = pipeline["ai"]["commands"]
    for host, cmd in commands.items():
        assert "{model_flag}" in cmd, f"ai.commands.{host} 缺少 {{model_flag}}"
