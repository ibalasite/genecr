from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


def _find_git_bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        str(Path.home() / "AppData/Local/Programs/Git/bin/bash.exe"),
    ):
        if Path(candidate).exists():
            return candidate

    resolved = shutil.which("bash")
    if resolved and "System32\\bash.exe" not in resolved:
        return resolved
    return None


def test_setup_sh_includes_copilot_runtime_and_target(repo_root: Path):
    content = (repo_root / "setup").read_text(encoding="utf-8")
    assert 'copilot) echo "$HOME/.copilot/skills/genecr"' in content
    assert 'copilot) echo "$HOME/.copilot/skills"' in content
    assert '*"/.copilot/"*) echo "copilot"' in content
    assert re.search(r'claude\|codex\|gemini\|copilot\|all', content)


def test_setup_ps1_includes_copilot_runtime_and_target(repo_root: Path):
    content = (repo_root / "setup.ps1").read_text(encoding="utf-8")
    assert '"copilot" { Join-Path $env:USERPROFILE ".copilot\\skills\\genecr" }' in content
    assert '"copilot" { Join-Path $env:USERPROFILE ".copilot\\skills" }' in content
    assert "elseif ($self -match '\\\\\\.copilot\\\\')" in content
    assert re.search(r'claude\|codex\|gemini\|copilot\|all', content)


def test_genecr_env_ps1_detects_copilot_host(repo_root: Path, tmp_path: Path):
    runtime = tmp_path / ".copilot" / "skills" / "genecr"
    runtime.mkdir(parents=True)
    script = repo_root / "bin" / "genecr-env.ps1"
    cmd = (
        f"$env:GENECR_DIR = '{runtime}'; "
        f". '{script}'; "
        "Write-Output $env:GENECR_HOST"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "copilot"


def test_genecr_env_sh_detects_copilot_host(repo_root: Path, tmp_path: Path):
    bash = _find_git_bash()
    if not bash:
        pytest.skip("Git Bash not available")

    runtime = tmp_path / ".copilot" / "skills" / "genecr"
    runtime.mkdir(parents=True)
    script = (repo_root / "bin" / "genecr-env.sh").as_posix()
    runtime_posix = runtime.as_posix()
    command = (
        f'export GENECR_DIR="{runtime_posix}"; '
        f'source "{script}"; '
        'printf "%s" "$GENECR_HOST"'
    )
    result = subprocess.run(
        [bash, "-lc", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "copilot"
