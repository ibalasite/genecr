"""db_queries 應該 inline 在對應 data_model 區塊下方，不要分開列導致讀者上下翻。

Preprocess 把 db_queries 依 used_indexes / SQL 字串對應到 data_models[i]，
塞進 data_models[i]['_related_queries']；template 直接讀。
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


def _spec_advanced_fixture():
    return {
        "feature": {"name": "f", "slug": "f"},
        "architecture": {"overview": "x", "diagram": "flowchart LR", "data_flow": "x"},
        "client": {"scene": "x", "components": [], "states": [], "update_strategy": "x", "performance": "x"},
        "apis": [],
        "data_models": [
            {"name": "users", "kind": "mysql",
             "fields": [{"name": "id", "type": "BIGINT"}],
             "indexes": [{"name": "uniq_users_email", "columns": ["email"]}],
             "create_table_sql": "CREATE TABLE users (...);"},
            {"name": "orders", "kind": "mysql",
             "fields": [{"name": "id", "type": "BIGINT"}],
             "indexes": [{"name": "idx_orders_user", "columns": ["user_id"]}],
             "create_table_sql": "CREATE TABLE orders (...);"},
        ],
        "db_queries": [
            {"scenario": "依 email 查 user",
             "sql": "SELECT * FROM users WHERE email = ?",
             "used_indexes": ["uniq_users_email"]},
            {"scenario": "查 user 訂單",
             "sql": "SELECT * FROM orders WHERE user_id = ?",
             "used_indexes": ["idx_orders_user"]},
        ],
        "business_logic": [], "cache_strategy": [], "redis_ops": [],
    }


def test_preprocess_attaches_related_queries_to_table():
    import render
    data = _spec_advanced_fixture()
    out = render.preprocess("spec-advanced", data, Path("."))
    users = next(m for m in out["data_models"] if m["name"] == "users")
    orders = next(m for m in out["data_models"] if m["name"] == "orders")
    assert users.get("_related_queries"), "users table missing _related_queries"
    assert orders.get("_related_queries"), "orders table missing _related_queries"
    assert users["_related_queries"][0]["scenario"] == "依 email 查 user"
    assert orders["_related_queries"][0]["scenario"] == "查 user 訂單"


def test_preprocess_uses_sql_fallback_when_no_used_indexes():
    """Query without used_indexes — preprocess should still attach to table
    via SQL string regex (`FROM tablename`)."""
    import render
    data = _spec_advanced_fixture()
    data["db_queries"][0].pop("used_indexes")  # remove index hint
    out = render.preprocess("spec-advanced", data, Path("."))
    users = next(m for m in out["data_models"] if m["name"] == "users")
    assert any(q["scenario"] == "依 email 查 user" for q in users.get("_related_queries", [])), (
        "SQL-fallback mapping (FROM users) should still attach the query"
    )


def test_preprocess_marks_unmapped_queries_as_orphan():
    """Query that can't be mapped to any table — preprocess collects into
    `_orphan_queries` so they're rendered somewhere (not silently dropped)."""
    import render
    data = _spec_advanced_fixture()
    data["db_queries"].append({
        "scenario": "跨表 join",
        "sql": "SELECT * FROM nonexistent_table x WHERE x.id = 1",
        "used_indexes": [],
    })
    out = render.preprocess("spec-advanced", data, Path("."))
    orphans = out.get("_orphan_queries", [])
    assert any(q["scenario"] == "跨表 join" for q in orphans), (
        "unmapped query must end up in _orphan_queries"
    )


def test_render_shows_query_inline_under_table():
    import render
    import re
    data = _spec_advanced_fixture()
    data = render.preprocess("spec-advanced", data, Path("."))
    md = render.render("spec-advanced", data)
    # Find the users table block (between '### users' heading and next '###')
    m = re.search(r"^###\s+users.*?(?=^###\s|\Z)", md, re.S | re.M)
    assert m, f"### users table block not found in render output"
    users_block = m.group(0)
    assert "依 email 查 user" in users_block, (
        f"scenario must render inline within users table block; got:\n{users_block[:600]}"
    )


def test_render_does_not_have_separate_db_queries_section():
    """Independent '## db_queries' / '## 情境 SQL' top-level section should
    be removed (queries are now inline). Cross-table queries may still live
    under a small orphan section."""
    import render
    data = render.preprocess("spec-advanced", _spec_advanced_fixture(), Path("."))
    md = render.render("spec-advanced", data)
    # Don't expect the legacy section heading
    assert "情境 SQL 範例" not in md or "跨" in md, (
        "legacy '情境 SQL 範例' top-level section should be removed; "
        "only an orphan cross-table summary may remain"
    )
