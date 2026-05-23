from __future__ import annotations

from pathlib import Path


def test_root_skill_mentions_copilot_runtime_and_pipeline_entry(repo_root: Path):
    content = (repo_root / "SKILL.md").read_text(encoding="utf-8")
    assert ".copilot/skills/genecr" in content
    assert 'python "$GENECR_TOOLS/pipeline.py"' in content


def test_upgrade_skill_mentions_copilot_host(repo_root: Path):
    content = (repo_root / "skills" / "genecr-upgrade" / "SKILL.md").read_text(encoding="utf-8")
    assert ".copilot" in content
    assert "copilot" in content


def test_readme_mentions_copilot_install_and_skills_commands(repo_root: Path):
    content = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "~/.copilot/skills/genecr" in content
    assert "/skills list" in content
    assert "/skills info genecr" in content
