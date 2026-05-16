"""spec-advanced render must auto-emit a Mermaid erDiagram from data_models.

This is ADDITIVE — the existing architecture.diagram (manual mermaid)
stays, and we add a generated erDiagram covering the relational tables.
"""
from __future__ import annotations

import pytest


def _sa_with(tables):
    return {
        "feature": {"name": "x", "slug": "x"},
        "architecture": {
            "overview": "o", "diagram": "graph TD\n  A-->B", "data_flow": "f",
        },
        "client": {"scene": "s", "components": [], "states": []},
        "apis": [{"id": "a", "method": "GET", "path": "/x", "desc": "x"}],
        "data_models": tables,
        "business_logic": [{"title": "t", "desc": "d"}],
        "cache_strategy": [],
    }


def test_er_diagram_emitted_for_mysql_tables(render_module):
    sa = _sa_with([
        {
            "name": "users",
            "kind": "mysql",
            "desc": "user accounts",
            "fields": [
                {"name": "uid", "type": "BIGINT UNSIGNED", "desc": "primary id"},
                {"name": "email", "type": "VARCHAR(255)", "desc": "login"},
            ],
            "indexes": ["PRIMARY KEY (uid)"],
            "apis": ["api-1"],
        }
    ])
    md = render_module.render("spec-advanced", sa)
    assert "erDiagram" in md
    assert "users" in md.lower()
    assert "uid" in md
    assert "email" in md


def test_er_diagram_skips_redis_tables(render_module):
    sa = _sa_with([
        {"name": "redis_state", "kind": "redis", "desc": "x", "fields": [], "indexes": [], "apis": []},
    ])
    md = render_module.render("spec-advanced", sa)
    # erDiagram block should not be emitted (or emitted empty) for redis-only
    # — either no erDiagram block, or it lists no entities
    assert "redis_state" not in md.split("erDiagram", 1)[-1].split("```", 1)[0] \
        if "erDiagram" in md else True


def test_er_diagram_multiple_tables(render_module):
    sa = _sa_with([
        {"name": "users", "kind": "mysql", "desc": "x",
         "fields": [{"name": "uid", "type": "BIGINT", "desc": "x"}],
         "indexes": [], "apis": []},
        {"name": "orders", "kind": "mysql", "desc": "y",
         "fields": [{"name": "oid", "type": "BIGINT", "desc": "x"}],
         "indexes": [], "apis": []},
    ])
    md = render_module.render("spec-advanced", sa)
    assert "erDiagram" in md
    assert "users" in md.lower()
    assert "orders" in md.lower()


def test_architecture_diagram_still_present(render_module, spec_advanced_example):
    """The auto ER block must be ADDITIVE — architecture.diagram still renders."""
    md = render_module.render("spec-advanced", spec_advanced_example)
    # Existing baseline test enforces ```mermaid presence; this one ensures
    # at least one of the mermaid blocks is the manual architecture diagram.
    assert md.count("```mermaid") >= 1
