"""驗 checkin7v2 baseline 跑 anchor 公式回到 baseline 點數 (10/8/8/3)。

這份 test 鎖定「baseline 是公式 anchor」這個契約 — 如果未來改 anchor 數字或
公式結構，這 test 會立刻 fail，逼開發者主動更新 anchor。

api/mysql/redis 數量從 sb.dryrun.tech_counts 拿（step isolation 鐵律，不讀下游 sa）。
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cross_check import _per_role_points_anchor  # noqa: E402

BASELINE = Path(__file__).resolve().parents[3] / "output" / "checkin7v2-baseline"


def _load_baseline():
    sb = json.loads((BASELINE / "spec-basic.input.json").read_text(encoding="utf-8"))
    return sb


def test_baseline_server_eq_10():
    sb = _load_baseline()
    f = _per_role_points_anchor(sb)
    # 8 API × 5/8 + 4 MySQL × 3/4 + 4 Redis × 2/4 = 5 + 3 + 2 = 10
    assert abs(f["server_engineer"] - 10.0) < 0.01, \
        f"server expected 10.0, got {f['server_engineer']}"


def test_baseline_art_eq_8():
    sb = _load_baseline()
    f = _per_role_points_anchor(sb)
    # 43 件 × 8/43 = 8.0
    assert abs(f["art"] - 8.0) < 0.01


def test_baseline_client_eq_8():
    sb = _load_baseline()
    f = _per_role_points_anchor(sb)
    # 7 wireframe × 8/7 = 8.0
    assert abs(f["client_engineer"] - 8.0) < 0.01


def test_baseline_planner_eq_3():
    sb = _load_baseline()
    f = _per_role_points_anchor(sb)
    # 12 AC × 3/12 = 3.0
    assert abs(f["planner"] - 3.0) < 0.01


def test_baseline_team_weeks_eq_2():
    sb = _load_baseline()
    f = _per_role_points_anchor(sb)
    # max(10, 8, 8, 3) = 10 → ceil(10/5) = 2 週
    assert math.ceil(max(f.values()) / 5) == 2


def test_anchor_scale_example_red_envelope_server():
    """User 舉例：10 API + 5 MySQL + 6 Redis → server formula = 13.0"""
    sb = {
        "resource_counts": {"api_endpoints": 10},
        "dryrun": {"tech_counts": {"api_endpoints": 10, "db_tables": 5, "redis_keys": 6}},
    }
    f = _per_role_points_anchor(sb)
    # 10 × 5/8 + 5 × 3/4 + 6 × 2/4 = 6.25 + 3.75 + 3.0 = 13.0
    assert abs(f["server_engineer"] - 13.0) < 0.01


def test_no_dryrun_falls_back_to_resource_counts_api():
    """dryrun 缺失時，api_endpoints fallback 到 resource_counts.api_endpoints；mysql/redis 計 0"""
    sb = {"resource_counts": {"api_endpoints": 8}}
    f = _per_role_points_anchor(sb)
    # 只算 API: 8 × 5/8 = 5.0；mysql/redis = 0
    assert abs(f["server_engineer"] - 5.0) < 0.01
