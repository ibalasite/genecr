from __future__ import annotations

import json
from pathlib import Path

from ai_command import resolve_ai_command

# web search flag per host
_WEB_SEARCH_FLAGS = {
    "claude":  '--allowedTools "WebSearch"',
    "codex":   "--search",
    "gemini":  "--allowed-tools google_web_search",
    "copilot": "--allow-all-urls",
}

# ── pipeline.json 結構驗證 ────────────────────────────────────────────────────

def test_pipeline_json_commands_contain_web_search_for_all_hosts(repo_root: Path):
    """pipeline.json ai.commands 每個 host 的指令必須含 web search 參數。"""
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    commands = pipeline["ai"]["commands"]
    for host, flag in _WEB_SEARCH_FLAGS.items():
        assert host in commands, f"ai.commands.{host} 缺失"
        assert flag in commands[host], (
            f"ai.commands.{host} 缺少 web search 參數 {flag!r}"
        )


# ── resolve_ai_command: web search flag 保留 ─────────────────────────────────

def test_resolve_claude_retains_web_search_flag(monkeypatch, repo_root: Path):
    """resolve_ai_command for claude 結果含 --allowedTools WebSearch。"""
    monkeypatch.setenv("GENECR_HOST", "claude")
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    cmd = resolve_ai_command(pipeline["ai"])
    assert '--allowedTools "WebSearch"' in cmd
    assert "--model claude-haiku-4-5-20251001" in cmd


def test_resolve_codex_retains_web_search_flag(monkeypatch, repo_root: Path):
    """resolve_ai_command for codex 結果含 --search。"""
    monkeypatch.setenv("GENECR_HOST", "codex")
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    cmd = resolve_ai_command(pipeline["ai"])
    assert "--search" in cmd
    assert "--model gpt-5-mini" in cmd


def test_resolve_gemini_retains_web_search_flag(monkeypatch, repo_root: Path):
    """resolve_ai_command for gemini 結果含 --allowed-tools google_web_search。"""
    monkeypatch.setenv("GENECR_HOST", "gemini")
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    cmd = resolve_ai_command(pipeline["ai"])
    assert "--allowed-tools google_web_search" in cmd
    assert "--model gemini-2.5-flash" in cmd


def test_resolve_copilot_retains_web_search_flag(monkeypatch, repo_root: Path):
    """resolve_ai_command for copilot 結果含 --allow-all-urls。"""
    monkeypatch.setenv("GENECR_HOST", "copilot")
    pipeline = json.loads((repo_root / "pipeline.json").read_text(encoding="utf-8"))
    cmd = resolve_ai_command(pipeline["ai"])
    assert "--allow-all-urls" in cmd
    assert "--model gpt-5-mini" in cmd
