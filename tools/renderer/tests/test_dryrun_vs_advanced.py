"""spec-advanced 實際數量必須 >= spec-basic dryrun 估算（程式約束，非 AI 自評）。

check_dryrun_vs_advanced(sb, sa) 在 spec-advanced step 跑，比對：
- sa.apis 實際數 >= sb.dryrun.tech_counts.api_endpoints
- sa.data_models 非 redis 數 >= sb.dryrun.tech_counts.db_tables
- sa.data_models kind=redis 數 >= sb.dryrun.tech_counts.redis_keys
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cross_check import check_dryrun_vs_advanced


def _sb(api=3, db=2, redis=1):
    return {
        "dryrun": {
            "tech_counts": {
                "api_endpoints": api,
                "db_tables": db,
                "redis_keys": redis,
            }
        }
    }


def _sa(apis=3, mysql_tables=2, redis_keys=1):
    models = []
    for i in range(mysql_tables):
        models.append({"name": f"tbl_{i}", "kind": "mysql"})
    for i in range(redis_keys):
        models.append({"name": f"r_{i}", "kind": "redis"})
    return {
        "apis": [{"id": f"api-{i}"} for i in range(apis)],
        "data_models": models,
    }


def test_passes_when_sa_meets_dryrun():
    issues = check_dryrun_vs_advanced(_sb(3, 2, 1), _sa(3, 2, 1))
    assert issues == []


def test_passes_when_sa_exceeds_dryrun():
    """技術版比 basic 估得多是允許的。"""
    issues = check_dryrun_vs_advanced(_sb(3, 2, 1), _sa(5, 3, 2))
    assert issues == []


def test_flags_too_few_apis():
    issues = check_dryrun_vs_advanced(_sb(api=5), _sa(apis=3))
    cats = {i.category for i in issues}
    assert "sa_apis_below_dryrun" in cats


def test_flags_too_few_db_tables():
    issues = check_dryrun_vs_advanced(_sb(db=3), _sa(mysql_tables=1))
    cats = {i.category for i in issues}
    assert "sa_db_tables_below_dryrun" in cats


def test_flags_too_few_redis_keys():
    issues = check_dryrun_vs_advanced(_sb(redis=2), _sa(redis_keys=0))
    cats = {i.category for i in issues}
    assert "sa_redis_keys_below_dryrun" in cats


def test_no_dryrun_in_sb_skips_gracefully():
    """sb 沒有 dryrun 欄位時，不 crash，直接跳過。"""
    issues = check_dryrun_vs_advanced({}, _sa(3, 2, 1))
    assert issues == []
