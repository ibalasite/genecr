from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


def _read_output(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except Exception:
        return ""


def resolve_ai_command(ai_cfg: dict) -> str:
    """Resolve the host-specific AI command, with ai.command as legacy fallback.

    If ai.models.<host> is set, substitutes {model_flag} with --model <id>.
    If not set, substitutes {model_flag} with empty string.
    """
    host = os.environ.get("GENECR_HOST", "")
    commands = ai_cfg.get("commands") or {}

    if host and host in commands:
        template = commands[host]
    elif "command" in ai_cfg:
        template = ai_cfg["command"]
    else:
        raise KeyError(
            f"No AI command configured for host '{host}' "
            f"(expected ai.commands[{host}] or ai.command)"
        )

    model_id = (ai_cfg.get("models") or {}).get(host, "")
    model_flag = f"--model {model_id}" if model_id else ""
    return template.replace("{model_flag}", model_flag)


def format_ai_command(
    ai_command: str,
    *,
    prompt_path: Path,
    output_path: Path,
    brief_file: Path | None = None,
    repo_root: Path | None = None,
    model_flag: str = "",
) -> str:
    values = {
        "prompt": str(prompt_path),
        "output": str(output_path),
        "model_flag": model_flag,
    }
    if brief_file is not None:
        values["brief_file"] = str(brief_file)
    if repo_root is not None:
        values["repo_root"] = str(repo_root)
    return ai_command.format(**values)


@dataclass
class AICommandRunResult:
    cmd: str
    returncode: int
    stdout: str
    stderr: str
    file_content: str
    content: str


def run_ai_command(
    ai_command: str,
    *,
    prompt_path: Path,
    output_path: Path,
    brief_file: Path | None = None,
    repo_root: Path | None = None,
) -> AICommandRunResult:
    cmd = format_ai_command(
        ai_command,
        prompt_path=prompt_path,
        output_path=output_path,
        brief_file=brief_file,
        repo_root=repo_root,
    )
    if output_path.exists():
        output_path.unlink()

    completed = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    file_content = _read_output(output_path)
    content = file_content or stdout or stderr or ""

    if completed.returncode == 0 and content.strip() and not file_content:
        output_path.write_text(content, encoding="utf-8")
        file_content = content
        content = file_content

    return AICommandRunResult(
        cmd=cmd,
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
        file_content=file_content,
        content=content,
    )
