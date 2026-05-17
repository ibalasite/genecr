"""Cross-step consistency checks — pure program logic, no AI.

Pipeline orchestrator calls run_all_checks(step_name, all_step_data) after
each step's schema validation passes. Any returned Issues are fed to the
fixer subagent (independent from generator/reviewer) for correction.

Design principles:
- Counts are computed by parsing real structures, never trusted from AI.
- Resource categories are dynamic: spec-basic lists N kinds, we check N kinds.
- Missing upstream data → skip the relevant check, don't crash. Pipeline
  controls when each check is safe to run.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass
class Issue:
    step: str
    category: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


# ─── resource counts ────────────────────────────────────────────────────────

def _sum_count(value) -> int:
    """resource_counts entry can be an int or a nested dict of ints."""
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return sum(_sum_count(v) for v in value.values())
    return 0


def _normalize_type(t: str) -> str:
    """Canonicalize to lowercase singular: strip trailing 's' if any.

    Both 'images'/'image' → 'image'; 'voiceover' stays 'voiceover'.
    Both sides of a comparison reduce to the same form.
    """
    t = (t or "").strip().lower()
    if t.endswith("s") and len(t) > 1:
        t = t[:-1]
    return t


def check_resource_counts(spec_basic_data: dict, assets_data: dict) -> list[Issue]:
    counts = spec_basic_data.get("resource_counts") or {}
    if not counts:
        return []

    # Count actual assets per (type, category) bucket
    actual_total: dict[str, int] = {}            # type → total count
    actual_sub: dict[str, dict[str, int]] = {}   # type → { category → count }
    for a in assets_data.get("assets", []):
        t = _normalize_type(a.get("type", ""))
        if not t:
            continue
        actual_total[t] = actual_total.get(t, 0) + 1
        sub = a.get("category")
        if sub:
            actual_sub.setdefault(t, {})
            actual_sub[t][sub] = actual_sub[t].get(sub, 0) + 1

    issues: list[Issue] = []
    for cat, declared_value in counts.items():
        # Skip non-resource bookkeeping fields
        if cat in {"modules", "acceptance_criteria", "api_endpoints"}:
            continue
        n_type = _normalize_type(cat)
        if isinstance(declared_value, dict):
            # Nested: check each sub-category
            actual_sub_map = actual_sub.get(n_type, {})
            for sub_name, sub_n in declared_value.items():
                actual_n = actual_sub_map.get(sub_name, 0)
                if sub_n != actual_n:
                    issues.append(Issue(
                        step="assets",
                        category="resource_count_mismatch",
                        detail=(
                            f"'{cat}.{sub_name}': spec-basic declares {sub_n}, "
                            f"assets has {actual_n} entries with category='{sub_name}'"
                        ),
                    ))
            # Also check no extra subs in assets that spec-basic didn't declare
            for sub_name in actual_sub_map:
                if sub_name not in declared_value:
                    issues.append(Issue(
                        step="assets",
                        category="resource_count_mismatch",
                        detail=(
                            f"assets has category '{cat}.{sub_name}' "
                            f"({actual_sub_map[sub_name]} items) not declared in spec-basic"
                        ),
                    ))
        else:
            # Flat int — total count comparison
            declared = _sum_count(declared_value)
            actual_n = actual_total.get(n_type, 0)
            if declared != actual_n:
                issues.append(Issue(
                    step="assets",
                    category="resource_count_mismatch",
                    detail=(
                        f"category '{cat}': spec-basic declares {declared}, "
                        f"assets lists {actual_n}"
                    ),
                ))
    return issues


# ─── timeline ↔ scrum points alignment ──────────────────────────────────────

def _role_budget_days(spec_basic: dict, spec_advanced: dict | None) -> dict[str, float]:
    """Per-role work-day budget calibrated to user's 10-day anchor on a
    6 wf / 8 api / 7 tables / 30 sub-cats case."""
    wf_n = len(spec_basic.get("wireframes") or [])
    api_n = len((spec_advanced or {}).get("apis") or [])
    table_n = len((spec_advanced or {}).get("data_models") or [])
    sub_cats = 0
    rc = spec_basic.get("resource_counts") or {}
    for k, v in rc.items():
        if k in {"modules", "acceptance_criteria", "api_endpoints"}:
            continue
        if isinstance(v, dict):
            sub_cats += len(v)
    return {
        "client_engineer": wf_n * 0.5,
        "server_engineer": api_n * 0.4 + table_n * 0.2,
        "art":             sub_cats * 0.05,
        "planner":         1.0,
        "po":              0.5,
    }


def check_timeline_against_formula(spec_basic: dict, spec_advanced: dict | None) -> list[Issue]:
    """For spec-basic step: timeline_weeks vs formula expected_weeks.
    Does NOT touch scrum (different fixer owner)."""
    total_expected_days = sum(_role_budget_days(spec_basic, spec_advanced).values())
    expected_weeks = total_expected_days / 5
    total_weeks = sum(t.get("duration_weeks", 0) or 0
                      for t in (spec_basic.get("timeline") or []) if isinstance(t, dict))
    if total_weeks > expected_weeks * 1.3 and expected_weeks >= 0.5:
        return [Issue(
            step="spec-basic",
            category="timeline_overestimated",
            detail=(
                f"timeline 總週數 {total_weeks} 超過公式預估 {expected_weeks:.1f} 週"
                f" × 1.3 = {expected_weeks*1.3:.1f} 週（總工作天 {total_expected_days:.1f}/5）"
            ),
        )]
    return []


def check_scrum_workload(
    spec_basic: dict,
    spec_advanced: dict | None,
    scrum: dict | None,
) -> list[Issue]:
    """For scrum step: per-role + total points vs formula. Does NOT touch
    spec-basic.timeline (different fixer owner)."""
    expected = _role_budget_days(spec_basic, spec_advanced)
    total_expected = sum(expected.values())

    actual: dict[str, int] = {}
    for s in (scrum or {}).get("stories", []) or []:
        if not isinstance(s, dict):
            continue
        r = s.get("owner_role", "?")
        actual[r] = actual.get(r, 0) + (s.get("points", 0) or 0)
    total_actual = sum(actual.values())

    issues: list[Issue] = []
    for role, exp in expected.items():
        act = actual.get(role, 0)
        max_act = max(exp * 1.3, 1.0)
        if act > max_act:
            issues.append(Issue(
                step="scrum",
                category="oversized_story",
                detail=(
                    f"{role} 實際 {act} 點 vs 公式預估 {exp:.1f} 點（上限 {max_act:.1f}）"
                    f" — 切太細或估點太高；建議拆分或合併 stories"
                ),
            ))
    if total_actual > total_expected * 1.3:
        issues.append(Issue(
            step="scrum",
            category="oversized_story",
            detail=(
                f"總點數 {total_actual} 超過公式預估 {total_expected:.1f} × 1.3 = "
                f"{total_expected*1.3:.1f}（量體公式: wireframes×0.5 + apis×0.4 "
                f"+ tables×0.2 + asset_sub_cats×0.05 + planner 1 + po 0.5）"
            ),
        ))
    return issues


# Kept for backward-compat with existing tests; delegates to the split funcs.
def check_role_workload_against_formula(spec_basic, spec_advanced, assets, scrum):
    return (check_scrum_workload(spec_basic, spec_advanced, scrum)
            + check_timeline_against_formula(spec_basic, spec_advanced))


def check_scope_against_wireframes(spec_basic_data: dict, scrum_data: dict) -> list[Issue]:
    """Wireframe-anchored objective scope cap.

    Cures the bug where LLM reviewer subjectively classifies a feature as
    "medium" and lets 7-week / 52-point estimates through. wireframe count
    is the concrete proxy for screen scope:
      max_total_weeks  ≈ wireframe_count × 0.5
      max_total_points ≈ wireframe_count × 2.5
    Tolerance ±30% (narrower than the ±50% old timeline-vs-points ratio,
    which permitted dual inflation on both sides).
    """
    wf_n = len(spec_basic_data.get("wireframes") or [])
    if wf_n == 0:
        return []
    max_weeks = wf_n * 0.5 * 1.3   # +30% headroom
    max_points = wf_n * 2.5 * 1.3

    issues: list[Issue] = []

    total_weeks = sum(t.get("duration_weeks", 0) or 0
                      for t in (spec_basic_data.get("timeline") or [])
                      if isinstance(t, dict))
    if total_weeks > max_weeks:
        issues.append(Issue(
            step="spec-basic",
            category="timeline_overestimated",
            detail=(
                f"timeline 總週數 {total_weeks} 超過 wireframes={wf_n} 的合理上限 "
                f"{max_weeks:.1f} 週（公式: wireframes × 0.5 × 1.3 headroom）。"
                f"有 AI 協助，{wf_n} 頁畫面應該 ≤ {max_weeks:.1f} 週。"
            ),
        ))

    if scrum_data:
        total_points = sum(s.get("points", 0) or 0
                           for s in (scrum_data.get("stories") or [])
                           if isinstance(s, dict))
        if total_points > max_points:
            issues.append(Issue(
                step="scrum",
                category="oversized_story",
                detail=(
                    f"scrum 總點數 {total_points} 超過 wireframes={wf_n} 的合理上限 "
                    f"{max_points:.1f} 點（公式: wireframes × 2.5 × 1.3 headroom）。"
                    f"{wf_n} 頁畫面活動應 ≤ {max_points:.1f} 點。檢查是否切太細或估點太高。"
                ),
            ))
    return issues


def check_timeline_vs_scrum_points(spec_basic_data: dict, scrum_data: dict) -> list[Issue]:
    """1 週 ≈ 5 點 (1 點 = 1 工作天). 兩邊規模需匹配 (容差 ±50%)."""
    timeline = spec_basic_data.get("timeline") or []
    total_weeks = sum(t.get("duration_weeks", 0) or 0 for t in timeline if isinstance(t, dict))
    stories = scrum_data.get("stories") or []
    total_points = sum(s.get("points", 0) or 0 for s in stories if isinstance(s, dict))
    if total_weeks <= 0 or total_points <= 0:
        return []
    expected_points = total_weeks * 5
    ratio = total_points / expected_points
    if ratio < 0.5 or ratio > 1.5:
        return [Issue(
            step="scrum",
            category="timeline_scrum_mismatch",
            detail=(
                f"scrum 總點數 {total_points} 與 spec-basic.timeline 總週數 {total_weeks} "
                f"× 5 = 期望 {expected_points} 點不符（容差 ±50%）；ratio={ratio:.2f}"
            ),
        )]
    return []


# ─── scenario count ─────────────────────────────────────────────────────────

def _get_acceptance_count(spec_basic_data: dict) -> int:
    rc = spec_basic_data.get("resource_counts") or {}
    if "acceptance_criteria" in rc:
        v = rc["acceptance_criteria"]
        return v if isinstance(v, int) else 0
    ac = spec_basic_data.get("acceptance_criteria")
    if isinstance(ac, list):
        return len(ac)
    return 0


def _get_api_count(spec_advanced_data: dict) -> int:
    rc = (spec_advanced_data.get("counts") or {})
    if "api_endpoints" in rc:
        v = rc["api_endpoints"]
        return v if isinstance(v, int) else 0
    apis = spec_advanced_data.get("apis")
    if isinstance(apis, list):
        return len(apis)
    return 0


def check_scenario_count(
    bdd_data: dict, spec_basic_data: dict, spec_advanced_data: dict
) -> list[Issue]:
    needed = _get_acceptance_count(spec_basic_data) + _get_api_count(spec_advanced_data)
    if needed == 0:
        return []
    got = len(bdd_data.get("scenarios", []))
    if got < needed:
        return [Issue(
            step="bdd",
            category="scenario_count_insufficient",
            detail=(
                f"need at least {needed} scenarios "
                f"(acceptance_criteria + api_endpoints); got {got}"
            ),
        )]
    return []


# ─── SQL index alignment ────────────────────────────────────────────────────

_WHERE_RE = re.compile(r"WHERE\s+(.+?)(?:\s+ORDER\s+BY|\s+GROUP\s+BY|\s+LIMIT|;|$)",
                       re.IGNORECASE | re.DOTALL)
_COL_RE = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|<|>|<=|>=|!=|IN|LIKE|BETWEEN)",
                     re.IGNORECASE)


def _columns_in_where(sql: str) -> list[str]:
    m = _WHERE_RE.search(sql or "")
    if not m:
        return []
    where = m.group(1)
    return [c.lower() for c in _COL_RE.findall(where)]


def _columns_in_indexes(indexes) -> set[str]:
    """Extract column names from an indexes list (each entry can be a string
    like 'INDEX idx_email (email)' or a dict)."""
    cols: set[str] = set()
    if not isinstance(indexes, list):
        return cols
    for idx in indexes:
        if isinstance(idx, str):
            # Capture anything in parens
            for m in re.finditer(r"\(([^)]+)\)", idx):
                for c in m.group(1).split(","):
                    cols.add(c.strip().lower())
        elif isinstance(idx, dict):
            for key in ("columns", "fields", "cols"):
                v = idx.get(key)
                if isinstance(v, list):
                    cols.update(str(c).lower() for c in v)
                elif isinstance(v, str):
                    cols.add(v.lower())
    return cols


def check_sql_index_alignment(spec_advanced_data: dict) -> list[Issue]:
    queries = spec_advanced_data.get("db_queries") or []
    if not queries:
        return []

    # Union of indexable columns across all relational tables
    all_indexed: set[str] = set()
    for tbl in spec_advanced_data.get("data_models", []):
        if tbl.get("kind") in {"redis", "memcached"}:
            continue
        all_indexed |= _columns_in_indexes(tbl.get("indexes"))

    issues: list[Issue] = []
    for q in queries:
        sql = q.get("sql", "")
        cols = _columns_in_where(sql)
        unindexed = [c for c in cols if c not in all_indexed]
        if unindexed:
            issues.append(Issue(
                step="spec-advanced",
                category="sql_no_matching_index",
                detail=(
                    f"scenario '{q.get('scenario', '?')}': "
                    f"WHERE columns {unindexed} not covered by any index"
                ),
            ))
    return issues


# ─── Redis key alignment ────────────────────────────────────────────────────

def check_redis_key_alignment(spec_advanced_data: dict) -> list[Issue]:
    ops = spec_advanced_data.get("redis_ops") or []
    if not ops:
        return []

    declared: set[str] = set()
    for tbl in spec_advanced_data.get("data_models", []):
        if tbl.get("kind") != "redis":
            continue
        p = tbl.get("redis_pattern")
        if p:
            declared.add(p)

    issues: list[Issue] = []
    for op in ops:
        for key in op.get("accessed_keys", []):
            if key not in declared:
                issues.append(Issue(
                    step="spec-advanced",
                    category="redis_key_undeclared",
                    detail=(
                        f"scenario '{op.get('scenario', '?')}' accesses key "
                        f"'{key}' which is not in redis_schema"
                    ),
                ))
    return issues


# ─── orchestrator ───────────────────────────────────────────────────────────

def run_all_checks(step_name: str, all_step_data: dict) -> list[Issue]:
    """Run every check whose target step matches `step_name` AND whose
    required upstream data is present. Returns the union of resulting Issues."""
    sb = all_step_data.get("spec-basic") or {}
    sa = all_step_data.get("spec-advanced") or {}
    assets = all_step_data.get("assets") or {}
    bdd = all_step_data.get("bdd") or {}

    issues: list[Issue] = []

    scrum = all_step_data.get("scrum") or {}

    if step_name == "assets" and sb and assets:
        issues += check_resource_counts(sb, assets)

    if step_name == "bdd" and bdd:
        issues += check_scenario_count(bdd, sb, sa)

    if step_name == "scrum" and sb and scrum:
        # Scrum step owns per-role + total points checks.
        issues += check_scrum_workload(sb, sa, scrum)
    if step_name == "spec-basic" and sb:
        # spec-basic step ONLY checks its own timeline (no scrum coupling —
        # spec-basic fixer can't edit scrum.input.json stories).
        issues += check_timeline_against_formula(sb, sa)

    if step_name == "spec-advanced" and sa:
        issues += check_sql_index_alignment(sa)
        issues += check_redis_key_alignment(sa)

    return issues
