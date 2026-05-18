"""scrum 全鏈拔掉 teams — template / schema / canonical / cross_check / 渲染輸出
都不准再出現 `teams` 欄位或「負責團隊」字串。

歷史 bug：scrum.md.tmpl 寫死 `**負責團隊**：{% for t in story.teams %}`，
template 讀 teams 不讀 owner_role；schema 容許 teams 自由欄位繞過 owner_role
enum 守門，於是 AI 寫 `teams: ['QA', 'Copy']`（QA 不是我們角色）也通過。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = REPO_ROOT / "templates"

if str(REPO_ROOT / "tools" / "renderer") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "renderer"))


# ─── A. template 不引用 teams、label 用「角色」───────────────────────────


def test_scrum_template_uses_owner_role_not_teams():
    text = (TEMPLATES / "scrum.md.tmpl").read_text(encoding="utf-8")
    assert "story.teams" not in text, "scrum.md.tmpl must not read story.teams"
    assert "story.owner_role" in text, "scrum.md.tmpl must read story.owner_role"


def test_scrum_template_label_says_role_not_team():
    text = (TEMPLATES / "scrum.md.tmpl").read_text(encoding="utf-8")
    assert "負責團隊" not in text, "scrum.md.tmpl must not say 「負責團隊」"
    assert "負責角色" in text, "scrum.md.tmpl must say 「負責角色」"


# ─── B. schema 禁 teams 欄位 ─────────────────────────────────────────────


def test_scrum_schema_forbids_teams_field():
    schema = json.loads((TEMPLATES / "schemas" / "scrum.schema.json").read_text(encoding="utf-8"))
    story_props = schema["properties"]["stories"]["items"].get("properties", {})
    assert "teams" not in story_props, "scrum schema must not declare a `teams` field"
    # additionalProperties closed
    assert schema["properties"]["stories"]["items"].get("additionalProperties") is False, (
        "scrum stories.items must set additionalProperties: false"
    )


# ─── C. canonical 不含 teams ─────────────────────────────────────────────


def test_scrum_canonical_has_no_teams():
    ex = json.loads((TEMPLATES / "examples" / "scrum.input.json").read_text(encoding="utf-8"))
    for s in ex.get("stories", []):
        assert "teams" not in s, f"canonical story #{s.get('id')} still has teams field"


# ─── D. cross_check.check_scrum_no_teams_field ───────────────────────────


def test_check_scrum_no_teams_field_flags_legacy():
    from cross_check import check_scrum_no_teams_field
    data = {"stories": [{"id": 1, "title": "x", "owner_role": "server_engineer",
                          "teams": ["Server"]}]}
    issues = check_scrum_no_teams_field(data)
    cats = {i.category for i in issues}
    assert "scrum_stories_have_legacy_teams_field" in cats


def test_check_scrum_no_teams_field_passes_with_owner_role():
    from cross_check import check_scrum_no_teams_field
    data = {"stories": [{"id": 1, "title": "x", "owner_role": "server_engineer"}]}
    issues = check_scrum_no_teams_field(data)
    assert not issues


# ─── E. render output 無「負責團隊」字串 ─────────────────────────────────


def test_scrum_render_no_legacy_team_string():
    import render
    ex = json.loads((TEMPLATES / "examples" / "scrum.input.json").read_text(encoding="utf-8"))
    md = render.render("scrum", ex)
    assert "負責團隊" not in md, "rendered scrum.md still contains '負責團隊'"
    assert "負責角色" in md, "rendered scrum.md should show '負責角色'"
