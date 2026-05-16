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

    # Count actual assets per normalized type
    actual: dict[str, int] = {}
    for a in assets_data.get("assets", []):
        cat = _normalize_type(a.get("type", ""))
        if not cat:
            continue
        actual[cat] = actual.get(cat, 0) + 1

    issues: list[Issue] = []
    for cat, declared_value in counts.items():
        # Skip non-resource bookkeeping fields
        if cat in {"modules", "acceptance_criteria", "api_endpoints"}:
            continue
        declared = _sum_count(declared_value)
        actual_n = actual.get(_normalize_type(cat), 0)
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

    if step_name == "assets" and sb and assets:
        issues += check_resource_counts(sb, assets)

    if step_name == "bdd" and bdd:
        issues += check_scenario_count(bdd, sb, sa)

    if step_name == "spec-advanced" and sa:
        issues += check_sql_index_alignment(sa)
        issues += check_redis_key_alignment(sa)

    return issues
