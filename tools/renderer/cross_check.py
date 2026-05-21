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
from html.parser import HTMLParser


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
    # Per-type total only — subkey naming is a soft convention. Strict
    # subkey alignment is enforced via check_assets_matches_sb_totals plus
    # the visual_total / audio_total contract (single source of truth).
    for cat, declared_value in counts.items():
        if cat in {"modules", "acceptance_criteria", "api_endpoints",
                   "visual_total", "audio_total"}:
            continue
        n_type = _normalize_type(cat)
        declared = _sum_count(declared_value)
        actual_n = actual_total.get(n_type, 0)
        if declared != actual_n:
            issues.append(Issue(
                step="assets",
                category="resource_count_mismatch",
                detail=(
                    f"type '{cat}': spec-basic declares {declared}, "
                    f"assets has {actual_n}"
                ),
            ))
    return issues


# ─── timeline ↔ scrum points alignment ──────────────────────────────────────

def _spec_basic_section_count(spec_basic: dict) -> int:
    """Count of spec-basic sections planner is responsible for."""
    return (
        len(spec_basic.get("user_journey") or []) +
        len(spec_basic.get("admin_journey") or []) +
        len((spec_basic.get("matrix") or {}).get("rows") or []) +
        5  # fixed: summary, axes, fields, rules, i18n, help_page
    )


# ─── ANCHOR：checkin7v2 baseline 固化的單一基準 ──────────────────
# 所有新企畫按量體比例縮放。1 點 = 1 工作天。
# 公式算出來是「地板」（最少要這麼多），scrum 拆 Fibonacci stories 自然 ≥ 地板，
# team 週數 = ceil(max(formula) / 5)，從公式算，不從 scrum 算。
_ANCHOR_SERVER_API   = (5, 8)   # 5 點 / 8 個 API endpoint
_ANCHOR_SERVER_MYSQL = (3, 4)   # 3 點 / 4 個 MySQL table
_ANCHOR_SERVER_REDIS = (2, 4)   # 2 點 / 4 個 Redis pattern
_ANCHOR_ART          = (8, 43)  # 8 點 / 43 件資源（visual + audio）
_ANCHOR_CLIENT       = (8, 7)   # 8 點 / 7 頁 wireframe
_ANCHOR_PLANNER      = (3, 12)  # 3 點 / 12 條 acceptance_criteria


def _per_role_points_anchor(spec_basic: dict) -> dict[str, float]:
    """每 role 按 anchor 比例算出「地板點數」（= 工作天）。

    純 spec-basic 自洽：api/mysql/redis 數量從 sb.dryrun.tech_counts 拿（AI 在 basic
    步驟自報的預估值）。不依賴下游 spec_advanced，符合 step isolation 鐵律。
    """
    rc = spec_basic.get("resource_counts") or {}
    tc = (spec_basic.get("dryrun") or {}).get("tech_counts") or {}
    n_api    = int(tc.get("api_endpoints", 0) or 0)
    n_mysql  = int(tc.get("db_tables", 0) or 0)
    n_redis  = int(tc.get("redis_keys", 0) or 0)
    n_asset  = int(rc.get("visual_total", 0) or 0) + int(rc.get("audio_total", 0) or 0)
    n_wf     = len(spec_basic.get("wireframes") or [])
    n_ac     = int(rc.get("acceptance_criteria", 0) or 0)

    server = (
        n_api   * _ANCHOR_SERVER_API[0]   / _ANCHOR_SERVER_API[1] +
        n_mysql * _ANCHOR_SERVER_MYSQL[0] / _ANCHOR_SERVER_MYSQL[1] +
        n_redis * _ANCHOR_SERVER_REDIS[0] / _ANCHOR_SERVER_REDIS[1]
    )
    return {
        "server_engineer": server,
        "art":             n_asset * _ANCHOR_ART[0]     / _ANCHOR_ART[1],
        "client_engineer": n_wf    * _ANCHOR_CLIENT[0]  / _ANCHOR_CLIENT[1],
        "planner":         n_ac    * _ANCHOR_PLANNER[0] / _ANCHOR_PLANNER[1],
    }


def _role_budget_days(spec_basic: dict) -> dict[str, float]:
    """Per-role work-day budget — **pure spec-basic self-contained**.
    Calibrated to checkin7v2 case as 1.0× anchor:
    - art          0.2 day per asset (from sb.resource_counts art types sum)
    - server_eng   1.0 day per API (from sb.dryrun.tech_counts.api_endpoints, AI 自報)
    - client_eng   0.67 day per wireframe (sb.wireframes count)
    - planner      0.2 day per spec section (sb sections derived)

    PO 不出現在 budget（不開 work-item story）。
    禁止讀 sa / assets / 任何下游 sibling — spec-basic 自有 bookkeeping 為準。
    """
    wf_n = len(spec_basic.get("wireframes") or [])
    rc = spec_basic.get("resource_counts") or {}
    tc = (spec_basic.get("dryrun") or {}).get("tech_counts") or {}
    api_n = int(tc.get("api_endpoints", 0) or 0)
    asset_n = 0
    for k, v in rc.items():
        if k in {"modules", "acceptance_criteria"}:
            continue
        if isinstance(v, dict):
            asset_n += sum(int(x) for x in v.values() if isinstance(x, (int, float)))
    section_n = _spec_basic_section_count(spec_basic)
    return {
        "art":             asset_n * 0.2,
        "server_engineer": api_n * 1.0,
        "client_engineer": wf_n * 0.67,
        "planner":         max(section_n * 0.2, 0.5),
    }


def _elapsed_weeks_from_role_budget(budget: dict[str, float]) -> int:
    """4 主要 role 平行做，elapsed = ceil(max(per-role-days) / 5).
    無條件進位成整數週 — 半週半天不能上線，必須整週規劃。"""
    import math
    if not budget:
        return 0
    return math.ceil(max(budget.values()) / 5)


_MAIN_ROLES = ("server_engineer", "client_engineer", "art", "planner")


def check_per_role_points_floor(scrum_data: dict, formula: dict) -> list[Issue]:
    """Per-role 地板檢查：scrum 加總 >= ceil(formula).

    地板邏輯：公式算出的點數 = 最少要這麼多。scrum 拆 Fibonacci stories（1/2/3/5/8）
    時自然會 ≥ 地板（拆分只可能等於或溢出）。所以**沒有 cap、只有 floor**。
    team 週數從 formula 算，不從 scrum 算，所以 Fibonacci 溢出不影響規劃週數。
    """
    import math
    issues: list[Issue] = []
    actual: dict[str, int] = {r: 0 for r in _MAIN_ROLES}
    for s in (scrum_data.get("stories") or []):
        r = s.get("owner_role")
        if r in actual:
            actual[r] += s.get("points", 0) or 0
    for role in _MAIN_ROLES:
        pts = actual[role]
        floor = math.ceil(formula.get(role, 0))
        if floor > 0 and pts < floor:
            issues.append(Issue(
                step="scrum",
                category="role_points_below_floor",
                detail=(
                    f"{role} 加總 {pts} 點 < 公式地板 {floor} 點 "
                    f"（公式 {formula[role]:.2f} 工作天 ceil 取整）。"
                    f"請補 stories 直到加總 ≥ {floor}（Fibonacci 拆分允許自然溢出）。"
                ),
            ))
    return issues


def check_per_story_points_cap(scrum_data: dict) -> list[Issue]:
    """任一 story.points > 5 → 太大必拆 (INVEST Small)."""
    issues: list[Issue] = []
    for s in (scrum_data.get("stories") or []):
        if (s.get("points") or 0) > 5:
            issues.append(Issue(
                step="scrum",
                category="story_too_large_split_needed",
                detail=f"story {s.get('id', '?')} 點數 {s['points']} > 5 cap（per-story INVEST Small），請拆成 2-3 子 story",
            ))
    return issues


def check_epic_role_coverage(scrum_data: dict) -> list[Issue]:
    """4 主要 role 各必有 1 epic."""
    have = {e.get("owner_role") for e in (scrum_data.get("epics") or [])}
    missing = [r for r in _MAIN_ROLES if r not in have]
    if missing:
        return [Issue(
            step="scrum",
            category="epic_role_missing",
            detail=f"epics 缺角色：{missing}。4 主要 role (server_engineer / client_engineer / planner / art) 必各 1 epic",
        )]
    return []


def check_stories_belong_to_epic(scrum_data: dict) -> list[Issue]:
    """每 story.epic 必對應 epics[].id."""
    epic_ids = {e.get("id") for e in (scrum_data.get("epics") or [])}
    issues: list[Issue] = []
    for s in (scrum_data.get("stories") or []):
        eid = s.get("epic")
        if eid not in epic_ids:
            issues.append(Issue(
                step="scrum",
                category="story_no_epic_link",
                detail=f"story {s.get('id', '?')}.epic = {eid!r} 找不到對應 epic.id（known: {sorted(epic_ids)}）",
            ))
    return issues


def check_no_po_stories(scrum_data: dict) -> list[Issue]:
    """PO 不開 work-item story；任一 story owner_role=po → fail."""
    issues: list[Issue] = []
    for s in (scrum_data.get("stories") or []):
        if s.get("owner_role") == "po":
            issues.append(Issue(
                step="scrum",
                category="po_owner_role_used",
                detail=f"story {s.get('id', '?')} owner_role=po 違規。PO 不開 work-item story，工作體現在 epic.po_acceptance",
            ))
    return issues


def check_story_has_subtasks(scrum_data: dict) -> list[Issue]:
    """每 story 必含 subtasks 子項目（非空）."""
    issues: list[Issue] = []
    for s in (scrum_data.get("stories") or []):
        if not (s.get("subtasks") or []):
            issues.append(Issue(
                step="scrum",
                category="story_missing_subtasks",
                detail=f"story {s.get('id', '?')} 缺 subtasks 子項目清單（必含實際 deliverable 列表）",
            ))
    return issues


def check_timeline_against_formula(spec_basic: dict) -> list[Issue]:
    """spec-basic timeline check：用 anchor 公式算地板，必須等於 ceil(max/5)。

    純 sb 自洽：mysql/redis 從 sb.dryrun.tech_counts 拿，不看下游。
    """
    budget = _per_role_points_anchor(spec_basic)
    expected_weeks = _elapsed_weeks_from_role_budget(budget)
    total_weeks = sum(t.get("duration_weeks", 0) or 0
                      for t in (spec_basic.get("timeline") or []) if isinstance(t, dict))
    if expected_weeks <= 0:
        return []
    if total_weeks > expected_weeks:
        return [Issue(
            step="spec-basic",
            category="timeline_overestimated",
            detail=(
                f"timeline 總週數 {total_weeks} > 公式預估 ceil(max/5) = {expected_weeks} 週 "
                f"（max per-role budget = {max(budget.values()):.1f} 工作天）"
            ),
        )]
    if total_weeks < expected_weeks:
        return [Issue(
            step="spec-basic",
            category="timeline_underestimated",
            detail=(
                f"timeline 總週數 {total_weeks} < 公式預估 ceil(max/5) = {expected_weeks} 週 "
                f"（max per-role budget = {max(budget.values()):.1f} 工作天）"
                f"。請補 phase 或拉長至 {expected_weeks} 週"
            ),
        )]
    return []


def check_scrum_workload(spec_basic: dict, scrum: dict | None,
                         spec_advanced: dict | None = None) -> list[Issue]:
    """scrum step：per-role 地板 + 單 story cap + epic 覆蓋 + 不准 PO + subtasks 必填。

    用 anchor 公式算 per-role 地板（從 sb.dryrun.tech_counts 拿，spec_advanced 保留相容參數但不使用）。
    """
    if not scrum:
        return []
    formula = _per_role_points_anchor(spec_basic)
    return (check_per_role_points_floor(scrum, formula)
            + check_per_story_points_cap(scrum)
            + check_epic_role_coverage(scrum)
            + check_stories_belong_to_epic(scrum)
            + check_no_po_stories(scrum)
            + check_story_has_subtasks(scrum))


def check_assets_matches_sb_totals(spec_basic: dict, assets_data: dict) -> list[Issue]:
    """assets step contract: Counter(assets[].type) totals must equal
    sb.resource_counts.visual_total / audio_total (AI-self-reported in sb).
    """
    from collections import Counter
    if not (spec_basic and assets_data):
        return []
    issues: list[Issue] = []
    rc = spec_basic.get("resource_counts") or {}
    expected_visual = int(rc.get("visual_total", 0) or 0)
    expected_audio = int(rc.get("audio_total", 0) or 0)
    counts = Counter(a.get("type") for a in (assets_data.get("assets") or []))
    actual_visual = sum(counts.get(t, 0) for t in ("image", "animation", "particle", "video", "font"))
    actual_audio = counts.get("sound", 0)
    if actual_visual != expected_visual:
        issues.append(Issue(
            step="assets",
            category="assets_visual_total_mismatch",
            detail=f"sb.resource_counts.visual_total={expected_visual} but assets has {actual_visual} visual items",
        ))
    if actual_audio != expected_audio:
        issues.append(Issue(
            step="assets",
            category="assets_audio_total_mismatch",
            detail=f"sb.resource_counts.audio_total={expected_audio} but assets has {actual_audio} sound items",
        ))
    return issues


# 已刪除：check_scope_against_wireframes（wf-only `timeline_overestimated` + `oversized_story`）
#   → 取代為 _per_role_points_anchor + check_timeline_against_formula 的單一基準邏輯
# 已刪除：check_timeline_vs_scrum_points（`timeline_scrum_mismatch` ratio ±50%）
#   → 取代為地板邏輯：team 週數從公式算、scrum 從 floor 算，兩者無需直接綁定


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

_QPS_RE = __import__("re").compile(r"(QPS\s*\d+|req/s|/min|/sec)", __import__("re").I)


def check_dryrun_vs_advanced(spec_basic: dict, spec_advanced: dict) -> list[Issue]:
    """spec-advanced 實際數量必須 >= spec-basic dryrun 估算。

    basic 的 dryrun.tech_counts 是技術版的最低標準：
    - sa.apis 數 >= sb.dryrun.tech_counts.api_endpoints
    - sa.data_models 非 redis 數 >= sb.dryrun.tech_counts.db_tables
    - sa.data_models kind=redis 數 >= sb.dryrun.tech_counts.redis_keys
    """
    tc = (spec_basic.get("dryrun") or {}).get("tech_counts") or {}
    if not tc:
        return []

    issues: list[Issue] = []
    min_api = int(tc.get("api_endpoints", 0) or 0)
    min_db  = int(tc.get("db_tables", 0) or 0)
    min_redis = int(tc.get("redis_keys", 0) or 0)

    actual_api = len(spec_advanced.get("apis") or [])
    models = spec_advanced.get("data_models") or []
    actual_db    = sum(1 for m in models if isinstance(m, dict) and m.get("kind") != "redis")
    actual_redis = sum(1 for m in models if isinstance(m, dict) and m.get("kind") == "redis")

    if actual_api < min_api:
        issues.append(Issue(
            step="spec-advanced",
            category="sa_apis_below_dryrun",
            detail=f"sa.apis 實際 {actual_api} 個 < sb.dryrun.tech_counts.api_endpoints {min_api} 個",
        ))
    if actual_db < min_db:
        issues.append(Issue(
            step="spec-advanced",
            category="sa_db_tables_below_dryrun",
            detail=f"sa.data_models DB table 實際 {actual_db} 張 < sb.dryrun.tech_counts.db_tables {min_db} 張",
        ))
    if actual_redis < min_redis:
        issues.append(Issue(
            step="spec-advanced",
            category="sa_redis_keys_below_dryrun",
            detail=f"sa.data_models redis 實際 {actual_redis} 個 < sb.dryrun.tech_counts.redis_keys {min_redis} 個",
        ))
    return issues


def check_apis_postman_grade(spec_advanced_data: dict) -> list[Issue]:
    """Postman/OpenAPI-grade structural checks per apis[] entry.

    Mirrors review.md rules R10-R16 in code (program-counted, not AI self-report).
    Issues are scoped to step=spec-advanced — that's the fixer responsible.
    """
    issues: list[Issue] = []
    apis = spec_advanced_data.get("apis", [])
    write_methods = {"POST", "PUT", "PATCH"}

    for a in apis:
        api_id = a.get("id", "?")
        method = (a.get("method") or "").upper()

        # R10: auth must be object
        auth = a.get("auth")
        if not isinstance(auth, dict):
            issues.append(Issue(
                step="spec-advanced",
                category="api_auth_not_object",
                detail=f"apis[id={api_id}].auth must be object, got {type(auth).__name__}",
            ))
            auth = {}  # avoid cascade

        # R11: auth.required=true → type ∈ {bearer/api_key/cookie/basic}
        if auth.get("required") and auth.get("type") in (None, "", "none"):
            issues.append(Issue(
                step="spec-advanced",
                category="api_auth_required_no_type",
                detail=f"apis[id={api_id}].auth.required=true but type missing or 'none'",
            ))

        # R12: parameters must not contain in='body'
        for p in (a.get("parameters") or []):
            if p.get("in") == "body":
                issues.append(Issue(
                    step="spec-advanced",
                    category="api_params_contains_body",
                    detail=f"apis[id={api_id}].parameters has in='body' ({p.get('name')}); move to request_body.schema",
                ))

        # R13: POST/PUT/PATCH must have request_body.schema
        if method in write_methods:
            rb = a.get("request_body")
            if not (isinstance(rb, dict) and isinstance(rb.get("schema"), dict)):
                issues.append(Issue(
                    step="spec-advanced",
                    category="api_write_no_request_body",
                    detail=f"apis[id={api_id}] ({method}) missing request_body.schema",
                ))

        # R14: responses must have 2xx + 4xx
        responses = a.get("responses") or {}
        codes = [str(c) for c in responses.keys()]
        has_2xx = any(c.startswith("2") for c in codes)
        has_4xx = any(c.startswith("4") for c in codes)
        if not (has_2xx and has_4xx):
            issues.append(Issue(
                step="spec-advanced",
                category="api_responses_no_success_or_error",
                detail=f"apis[id={api_id}].responses must include 2xx + 4xx; got {sorted(codes)}",
            ))

        # R15: every response entry must have schema (not only example)
        for code, resp in responses.items():
            if not isinstance(resp, dict):
                continue
            if "example" in resp and not isinstance(resp.get("schema"), dict):
                issues.append(Issue(
                    step="spec-advanced",
                    category="api_response_no_schema",
                    detail=f"apis[id={api_id}].responses[{code}] has example but no schema",
                ))

        # R16: perf mentions QPS → rate_limit required
        perf = a.get("perf") or ""
        if _QPS_RE.search(perf) and not isinstance(a.get("rate_limit"), dict):
            issues.append(Issue(
                step="spec-advanced",
                category="api_rate_limit_missing",
                detail=f"apis[id={api_id}].perf mentions throughput ({perf!r}) but rate_limit not declared",
            ))

    return issues


_ADMIN_PATH_RE = __import__("re").compile(r"/(admin|internal|dashboard|console)/", __import__("re").I)
_UI_STORY_RE = __import__("re").compile(r"UI|介面|面板|列表|畫面|dashboard|console", __import__("re").I)
_ADMIN_NAME_RE = __import__("re").compile(r"後台|admin", __import__("re").I)


def _wireframe_covers(wireframes: list, needle: str) -> bool:
    """Fuzzy: any wireframe.name/desc contains needle (case-insensitive)."""
    needle_lc = needle.lower()
    for w in wireframes or []:
        hay = (w.get("name", "") + " " + w.get("desc", "")).lower()
        if needle_lc in hay:
            return True
    return False


def check_admin_wireframe_self_consistency(spec_basic_data: dict) -> list[Issue]:
    """spec-basic 純自洽 admin 結構檢查（不跨 doc）：
    - admin_journey 非空 → wireframes 必含 name 含 後台/admin 的條目
    - wireframes 任一 name 含 admin → admin_journey 必非空
    雙向 cross-validation 都在 sb 內，零下游依賴。
    """
    issues: list[Issue] = []
    aj = spec_basic_data.get("admin_journey") or []
    wfs = spec_basic_data.get("wireframes") or []
    has_admin_wf = any(_ADMIN_NAME_RE.search(w.get("name", "") or "") for w in wfs)

    if aj and not has_admin_wf:
        issues.append(Issue(
            step="spec-basic",
            category="admin_wireframe_missing_for_journey",
            detail=(f"spec-basic.admin_journey 有 {len(aj)} 步但 wireframes 找不到 "
                    "name 含「後台」/admin 的條目；請補對應 wireframe。"),
        ))
    if has_admin_wf and not aj:
        issues.append(Issue(
            step="spec-basic",
            category="admin_journey_missing",
            detail=("spec-basic.wireframes 有 admin/後台 條目但 admin_journey 為空；"
                    "請補對應 admin_journey 步驟。"),
        ))
    return issues


_DESKTOP_MARKER_RE = __import__("re").compile(
    r"width\s*[:=]\s*['\"]?\s*\d{4,}|class\s*=\s*['\"][^'\"]*(?:desktop|admin|dashboard|sidebar)|"
    r"後台|admin", __import__("re").I
)


def check_prototype_admin_coverage(spec_basic_data: dict, prototype_data: dict) -> list[Issue]:
    """If spec-basic has an admin wireframe, prototype_html must contain
    an admin demo (desktop layout marker or 後台/admin string)."""
    wireframes = spec_basic_data.get("wireframes", []) or []
    has_admin_wf = any(("後台" in w.get("name", "")) or
                       ("admin" in w.get("name", "").lower())
                       for w in wireframes)
    if not has_admin_wf:
        return []
    html = prototype_data.get("prototype_html", "") or ""
    if "後台" in html or "admin" in html.lower():
        return []
    return [Issue(
        step="prototype",
        category="prototype_admin_uncovered",
        detail="spec-basic.wireframes 含 admin/後台 條目，但 prototype_html 沒對應 demo；"
               "請補上後台桌面 layout 區塊（含「後台」字串 + desktop-width 容器）。",
    )]


_WF_PILL_RE = __import__("re").compile(r'class\s*=\s*["\']\s*wf-pill\b', __import__("re").I)


def check_admin_wireframe_dsl(spec_basic_data: dict) -> list[Issue]:
    """Admin wireframes (name 含 後台/admin) must use desktop DSL primitives
    (wf-desktop / wf-input / wf-table), not mobile/loading ones
    (wf-frame / wf-skeleton-pill / wf-pill rows faking tables).
    """
    issues: list[Issue] = []
    for w in (spec_basic_data.get("wireframes") or []):
        name = w.get("name", "")
        if not _ADMIN_NAME_RE.search(name):
            continue
        html = w.get("html", "") or ""

        # Container: must use wf-desktop / wf-desktop-app, NOT wf-frame
        if "wf-desktop" not in html:
            issues.append(Issue(
                step="spec-basic",
                category="admin_wireframe_wrong_container",
                detail=f"wireframe '{name}' 沒用 wf-desktop / wf-desktop-app 容器。後台必須用 desktop 容器，不准用 wf-frame（mobile/通用窄欄）。",
            ))

        # Form input: no wf-skeleton-pill (that's a loading placeholder)
        if "wf-skeleton-pill" in html:
            issues.append(Issue(
                step="spec-basic",
                category="admin_form_uses_skeleton_pill",
                detail=f"wireframe '{name}' 用 wf-skeleton-pill 當表單輸入。那是 shimmer 讀取佔位，後台表單請改用 wf-input / wf-input-date / wf-select / wf-textarea。",
            ))

        # Table fake from pills: any wf-row containing >= 4 wf-pill spans + no wf-table
        if "wf-table" not in html:
            # Look for wf-row with many wf-pill children
            import re
            for m in re.finditer(
                r'<div[^>]*class\s*=\s*["\'][^"\']*wf-row[^"\']*["\'][^>]*>(.*?)</div>',
                html, re.S,
            ):
                inner = m.group(1)
                pill_count = len(_WF_PILL_RE.findall(inner))
                if pill_count >= 4:
                    issues.append(Issue(
                        step="spec-basic",
                        category="admin_table_uses_pills",
                        detail=f"wireframe '{name}' 用一排 {pill_count} 個 wf-pill 假裝表格。pill 是小徽章不是儲存格，後台表格資料請改用 wf-table > wf-tr > wf-td。",
                    ))
                    break  # one report per wireframe is enough

    return issues


# ─── wf-row inline-only DSL guard ─────────────────────────────────────────
# wf-row 的直接 children 必須是 inline primitives；block primitives 塞進
# wf-row 會撐爆 mobile/desktop frame 寬度。modal 內部例外（modal 自有寬度，
# 兩欄選擇樣式 wf-modal-body > wf-row > wf-panel 是合法的）。

_WF_ROW_BLOCK_CLASSES = frozenset({
    "wf-panel", "wf-card", "wf-board", "wf-stage", "wf-banner",
    "wf-table", "wf-tr", "wf-td", "wf-modal", "wf-form-row",
    "wf-toolbar", "wf-pagination", "wf-cards-grid", "wf-stat-card",
    "wf-desktop", "wf-desktop-app", "wf-mobile", "wf-frame", "wf-info",
    "wf-appbar", "wf-statusbar", "wf-actionbar", "wf-breadcrumb",
    "wf-main", "wf-skeleton-block",
})


class _WfRowGuardParser(HTMLParser):
    """Walk a wireframe HTML; flag block-class elements that are direct
    children of any wf-row container — UNLESS that wf-row is inside a
    wf-modal subtree (modals have their own width)."""

    def __init__(self) -> None:
        super().__init__()
        # stack entries: dict(tag, is_row, in_modal)
        self.stack: list[dict] = []
        self.violations: list[str] = []  # offending class names

    def handle_starttag(self, tag, attrs):
        cls = ""
        for k, v in attrs:
            if k == "class":
                cls = v or ""
                break
        cls_set = set(cls.split())

        parent = self.stack[-1] if self.stack else None
        if parent and parent["is_row"] and not parent["in_modal"]:
            bad = cls_set & _WF_ROW_BLOCK_CLASSES
            if bad:
                self.violations.append(",".join(sorted(bad)))

        in_modal = bool(parent and parent["in_modal"]) or ("wf-modal" in cls_set)
        is_row = "wf-row" in cls_set
        self.stack.append({"tag": tag, "is_row": is_row, "in_modal": in_modal})

    def handle_startendtag(self, tag, attrs):
        # self-closing — push and pop equivalent of the open work only
        cls = ""
        for k, v in attrs:
            if k == "class":
                cls = v or ""
                break
        cls_set = set(cls.split())
        parent = self.stack[-1] if self.stack else None
        if parent and parent["is_row"] and not parent["in_modal"]:
            bad = cls_set & _WF_ROW_BLOCK_CLASSES
            if bad:
                self.violations.append(",".join(sorted(bad)))

    def handle_endtag(self, tag):
        # Pop the matching tag (tolerant: pop nearest matching).
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return


def check_wireframe_row_inline_only(spec_basic: dict) -> list[Issue]:
    """wf-row 的直接 children 必須是 inline DSL primitives。
    Block primitives (wf-panel / wf-card / wf-board / wf-banner / wf-table 等)
    當 wf-row 直接 child 會撐爆 mobile/desktop frame 寬度 → 違規。

    例外：wf-modal 子樹內的 wf-row 允許 block child（modal 自有寬度，
    side-by-side 選擇樣式 wf-modal-body > wf-row > wf-panel 屬合法 UI 樣式）。

    純自洽：只吃 spec_basic dict，不讀任何 sibling、不做 disk IO。
    """
    issues: list[Issue] = []
    for wf in (spec_basic.get("wireframes") or []):
        if not isinstance(wf, dict):
            continue
        html = wf.get("html") or ""
        if not html:
            continue
        parser = _WfRowGuardParser()
        try:
            parser.feed(html)
        except Exception:
            continue
        for bad in parser.violations:
            issues.append(Issue(
                step="spec-basic",
                category="wireframe_row_contains_block",
                detail=(
                    f"wireframe '{wf.get('name', '?')}' has block class "
                    f"'{bad}' directly inside wf-row — block primitives "
                    "overflow row width; use wf-pill/wf-tag/wf-btn (inline) "
                    "or move block out of row (e.g. wf-stage > wf-panel)."
                ),
            ))
    return issues


def check_scrum_no_teams_field(scrum_data: dict) -> list[Issue]:
    """scrum.stories[] must not contain `teams` legacy field. Use owner_role
    only — single multi-role team, no separate departments."""
    issues: list[Issue] = []
    for s in (scrum_data.get("stories") or []):
        if "teams" in s:
            issues.append(Issue(
                step="scrum",
                category="scrum_stories_have_legacy_teams_field",
                detail=f"story #{s.get('id', '?')} 含 `teams` 欄位 ({s.get('teams')!r})。"
                       f"我們是單一 scrum team，多角色組合；只用 owner_role enum "
                       f"(server_engineer/client_engineer/planner/po/art)，禁用 teams。",
            ))
    return issues


def check_prototype_layout_skeleton(spec_basic_data: dict, prototype_data: dict) -> list[Issue]:
    """prototype_html 必須用固定 layout skeleton：proto-page + proto-tabs +
    至少 2 個 proto-surface（player / admin）。若 spec-basic 有 admin
    wireframe，admin surface 不可為空。
    """
    issues: list[Issue] = []
    html = (prototype_data.get("prototype_html") or "")
    if "proto-page" not in html or "proto-tabs" not in html or "proto-surface" not in html:
        issues.append(Issue(
            step="prototype",
            category="prototype_layout_skeleton_missing",
            detail="prototype_html 缺 layout skeleton（必含 proto-page + proto-tabs + proto-surface 三個 class）。請依 prompt 中的固定 skeleton 結構填內容，不要自己刻 tabs 邏輯。",
        ))

    # admin surface non-empty if spec-basic has admin wireframes
    wireframes = spec_basic_data.get("wireframes") or []
    has_admin_wf = any(("後台" in w.get("name", "")) or ("admin" in w.get("name", "").lower())
                       for w in wireframes)
    if has_admin_wf:
        import re
        m = re.search(r'<[^>]*\bclass\s*=\s*["\'][^"\']*proto-surface[^"\']*["\'][^>]*data-surface\s*=\s*["\']admin["\'][^>]*>(.*?)</', html, re.S)
        if not m or len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", m.group(1)))) < 5:
            issues.append(Issue(
                step="prototype",
                category="prototype_admin_surface_empty",
                detail="spec-basic 有 admin/後台 wireframe，但 prototype_html 的 admin surface 內容空白或缺失。請在 data-surface=\"admin\" 容器內填後台桌面 demo。",
            ))
    return issues


# ─── prototype layout/UX guards (5 rules, pure text analysis) ─────────────
# 純文字/regex/HTMLParser — 不開瀏覽器、不做 IO、只吃 prototype dict。
# 每條規則的設計權衡：
# - 必須 catch exp1 已知 bug（regression 防線）
# - 不可誤殺 baseline（canonical reference）
# - 不可讀任何 sibling 檔（_no_disk_io guard）

_PROTO_CSS_RULE_RE = re.compile(
    r"([^{}/]+?)\s*\{([^{}]*)\}",
    re.S,
)
_PROTO_MEDIA_RE = re.compile(r"@media[^{]*\{(?:[^{}]|\{[^{}]*\})*\}", re.S)
_PROTO_PX_WIDTH_RE = re.compile(r"\bwidth\s*:\s*(\d+)px", re.I)
_PROTO_PX_MINWIDTH_RE = re.compile(r"\bmin-width\s*:\s*(\d+)px", re.I)
_PROTO_PX_MAXWIDTH_RE = re.compile(r"\bmax-width\s*:\s*(\d+)px", re.I)
_PROTO_PADDING_RE = re.compile(r"\bpadding(?:-left|-right|-inline|-inline-start|-inline-end)?\s*:\s*([^;]+)", re.I)
_PROTO_BOX_SIZING_BB_RE = re.compile(r"box-sizing\s*:\s*border-box", re.I)
_PROTO_GRID_REPEAT_RE = re.compile(
    r"grid-template-columns\s*:\s*repeat\(\s*(\d+)\s*,\s*([^)]+)\)",
    re.I,
)


def _proto_extract_styles(html: str) -> str:
    """Return concatenated text of all <style>...</style> blocks."""
    return "\n".join(re.findall(r"<style\b[^>]*>(.*?)</style>", html or "", re.S | re.I))


def _proto_iter_css_rules(css_text: str):
    """Yield (selector, body) for each CSS rule, stripping out @media wrappers."""
    # Naive but adequate: strip @media blocks first, then iterate remaining rules.
    flat = _PROTO_MEDIA_RE.sub("", css_text)
    for m in _PROTO_CSS_RULE_RE.finditer(flat):
        sel = m.group(1).strip()
        body = m.group(2)
        if sel.startswith("@"):
            continue
        yield sel, body


def _proto_has_universal_box_sizing(css_text: str) -> bool:
    """True iff any rule with selector containing '*' applies box-sizing:border-box."""
    for sel, body in _proto_iter_css_rules(css_text):
        if "*" in sel and _PROTO_BOX_SIZING_BB_RE.search(body):
            return True
    return False


def _proto_padding_has_nonzero(decl: str) -> bool:
    """Check if a padding shorthand declaration includes any non-zero numeric value."""
    # Strip !important etc, look for any digit
    parts = re.findall(r"(\d+(?:\.\d+)?)(px|em|rem|%)?", decl)
    return any(float(v) > 0 for v, _ in parts)


def check_proto_horizontal_overflow(prototype: dict) -> list[Issue]:
    """Detect horizontal-overflow patterns in prototype CSS.

    Two patterns flagged (both real-world causes of horizontal scroll on mobile):
    1. width:100% + padding:>0 WITHOUT box-sizing:border-box (universal or local)
       — classic content-box overflow; happens when AI forgets `* { box-sizing }`.
    2. grid-template-columns:repeat(N,1fr) parent where N × child min-width
       exceeds the parent's fixed pixel width.
    """
    issues: list[Issue] = []
    html = (prototype.get("prototype_html") or "")
    if not html:
        return issues
    css = _proto_extract_styles(html)
    if not css:
        return issues

    has_universal_bb = _proto_has_universal_box_sizing(css)

    # Pattern 1: width:100% + non-zero padding without box-sizing — but ONLY flag
    # NON-form-element selectors. Browsers (and most resets) handle form controls
    # (input/button/textarea/select) reasonably; the wide-spread bug is on
    # generic block selectors (.card, .row, .panel). Form selectors are
    # excluded to avoid noisy baseline regressions for `.btn-primary` etc.
    form_like_re = re.compile(
        r"(^|\s|,)(?:button|input|textarea|select|\.btn[\w-]*|\.[\w-]*-btn\b)",
        re.I,
    )
    for sel, body in _proto_iter_css_rules(css):
        if not re.search(r"\bwidth\s*:\s*100%", body, re.I):
            continue
        # local box-sizing OK
        if _PROTO_BOX_SIZING_BB_RE.search(body):
            continue
        if has_universal_bb:
            continue
        pad_match = _PROTO_PADDING_RE.search(body)
        if not pad_match or not _proto_padding_has_nonzero(pad_match.group(1)):
            continue
        if form_like_re.search(sel):
            continue
        issues.append(Issue(
            step="prototype",
            category="prototype_horizontal_overflow",
            detail=(
                f"selector '{sel[:80]}' uses width:100% + padding without box-sizing:border-box "
                f"and no universal `* {{ box-sizing: border-box }}` reset is declared. "
                "Result: element overflows its parent horizontally. "
                "Fix: add `*,*:before,*:after {{ box-sizing: border-box }}` near top of <style>."
            ),
        ))

    # Pattern 2: grid repeat(N, 1fr/Xpx) with child min-width that overflows parent
    # Build a map: selector -> fixed widths
    sel_width: dict[str, int] = {}
    sel_minwidth: dict[str, int] = {}
    for sel, body in _proto_iter_css_rules(css):
        wm = _PROTO_PX_WIDTH_RE.search(body)
        if wm:
            sel_width[sel] = int(wm.group(1))
        mwm = _PROTO_PX_MINWIDTH_RE.search(body)
        if mwm:
            sel_minwidth[sel] = int(mwm.group(1))

    # Look for parent.grid with repeat(N,1fr), parent class has fixed width or known ancestor with width
    for parent_sel, parent_body in _proto_iter_css_rules(css):
        gm = _PROTO_GRID_REPEAT_RE.search(parent_body)
        if not gm:
            continue
        n_cols = int(gm.group(1))
        track = gm.group(2).strip().lower()
        if "fr" not in track and "minmax" not in track:
            # Fixed-px tracks
            tm = re.search(r"(\d+)px", track)
            if not tm:
                continue
            track_w = int(tm.group(1))
        else:
            track_w = None  # 1fr — depends on parent width

        # Find any rule whose selector references this parent class + a child class
        # Cheap heuristic: any selector starting with parent_sel + " " + child
        parent_class = parent_sel.lstrip(".").split()[0].split(":")[0] if parent_sel.startswith(".") else None
        if not parent_class:
            continue

        # Estimate parent width (walk simple ancestor chain via HTML containment)
        # Use any selector that has fixed width and whose class appears as an ancestor
        # via simple HTML scan: find first ancestor with fixed width
        parent_width = _proto_estimate_parent_width(html, parent_class, sel_width)
        if not parent_width:
            continue

        # Find child min-width: any selector that is descendant of parent_class
        # Simple: scan all selectors that start with `.{parent_class} ` or `.cell` referenced inside parent
        for child_sel, child_minw in sel_minwidth.items():
            # Cheap: child class appears in HTML inside any element of parent_class
            child_class = child_sel.lstrip(".").split()[0].split(":")[0] if child_sel.startswith(".") else None
            if not child_class:
                continue
            if not _proto_class_is_descendant(html, parent_class, child_class):
                continue
            if track_w is not None:
                # Fixed-px tracks — straightforward sum
                total = n_cols * max(track_w, child_minw)
            else:
                # 1fr tracks — each column gets parent_width/n_cols; if min-width > that → overflow
                col_w = parent_width / n_cols
                if child_minw <= col_w:
                    continue
                total = n_cols * child_minw
            if total > parent_width:
                issues.append(Issue(
                    step="prototype",
                    category="prototype_horizontal_overflow",
                    detail=(
                        f"grid '{parent_sel}' has {n_cols} columns × child '{child_sel}' "
                        f"min-width:{child_minw}px → total {total}px > parent width {parent_width}px. "
                        "Fix: drop child min-width or use `repeat(N, minmax(0, 1fr))`."
                    ),
                ))
    return issues


def _proto_estimate_parent_width(html: str, parent_class: str, sel_width: dict[str, int]) -> int:
    """Find the nearest fixed-width ancestor of any element with parent_class.

    Walks the HTML, tracking class stack; when it enters an element whose class
    contains parent_class, returns the most recent ancestor's fixed width.
    Returns 0 if none found.
    """
    sel_to_w = {s.lstrip(".").split()[0].split(":")[0]: w for s, w in sel_width.items() if s.startswith(".")}

    class _AncestorParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.stack: list[set[str]] = []
            self.result: int = 0

        def handle_starttag(self, tag, attrs):
            cls = ""
            for k, v in attrs:
                if k == "class":
                    cls = v or ""; break
            cls_set = set(cls.split())
            if parent_class in cls_set and self.result == 0:
                # search ancestor chain (innermost first) for fixed width
                for anc in reversed(self.stack):
                    for c in anc:
                        if c in sel_to_w:
                            self.result = sel_to_w[c]
                            return
                # also check the element itself
                for c in cls_set:
                    if c in sel_to_w:
                        self.result = sel_to_w[c]
                        return
            self.stack.append(cls_set)

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

    p = _AncestorParser()
    try:
        p.feed(html)
    except Exception:
        return 0
    return p.result


def _proto_class_is_descendant(html: str, parent_class: str, child_class: str) -> bool:
    """True iff some element with class child_class appears inside an ancestor with class parent_class."""
    class _DescParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.depth_in_parent: int = 0
            self.found: bool = False

        def handle_starttag(self, tag, attrs):
            cls = ""
            for k, v in attrs:
                if k == "class":
                    cls = v or ""; break
            cls_set = set(cls.split())
            if parent_class in cls_set:
                self.depth_in_parent += 1
            elif self.depth_in_parent > 0 and child_class in cls_set:
                self.found = True

        def handle_endtag(self, tag):
            # Tolerant: only decrement; matching is approximate
            pass

    p = _DescParser()
    try:
        p.feed(html)
    except Exception:
        return False
    return p.found


# ─── dead nav item ───────────────────────────────────────────────────────

_PROTO_OPACITY_LOW_RE = re.compile(r"opacity\s*:\s*0?\.([0-6])\b", re.I)
_PROTO_CURSOR_DEFAULT_RE = re.compile(r"cursor\s*:\s*default", re.I)


def check_proto_dead_nav_item(prototype: dict) -> list[Issue]:
    """Flag <a> elements that look disabled/decorative (low opacity, cursor:default,
    disabled class, aria-disabled) but lack a real handler (onclick / href to a
    real anchor / data-page / data-pane / data-tab).

    Avoids false positives on non-nav decorative elements by restricting to <a> tags
    only — divs/spans with cursor:default styling (card decorations etc.) are
    excluded. <a> tags are nav by convention; a non-functional <a> is a UX bug.
    """
    issues: list[Issue] = []
    html = (prototype.get("prototype_html") or "")
    if not html:
        return issues

    # Find every <a ...>text</a> with attributes
    for m in re.finditer(r"<a\b([^>]*)>([^<]{0,200})</a>", html, re.I | re.S):
        attrs = m.group(1)
        text = m.group(2).strip()

        # Functional? has onclick, has href to non-# anchor, or data-page/pane/tab
        has_onclick = re.search(r"\bonclick\s*=", attrs, re.I) is not None
        href_m = re.search(r'\bhref\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        href = href_m.group(1) if href_m else None
        # href "#" or empty is not functional; "#something" with onclick is functional
        has_real_href = href is not None and href not in ("", "#", "javascript:void(0)")
        has_data_nav = re.search(r"\bdata-(page|pane|tab|surface|view)\s*=", attrs, re.I) is not None
        functional = has_onclick or has_real_href or has_data_nav

        # Disabled-looking? check style/class/aria
        style_m = re.search(r'\bstyle\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        style = style_m.group(1) if style_m else ""
        cls_m = re.search(r'\bclass\s*=\s*["\']([^"\']*)["\']', attrs, re.I)
        cls = cls_m.group(1) if cls_m else ""

        looks_disabled = (
            bool(_PROTO_OPACITY_LOW_RE.search(style))
            or bool(_PROTO_CURSOR_DEFAULT_RE.search(style))
            or bool(re.search(r"\baria-disabled\s*=", attrs, re.I))
            or "disabled" in cls.lower().split()
        )

        if looks_disabled and not functional:
            issues.append(Issue(
                step="prototype",
                category="prototype_dead_nav_item",
                detail=(
                    f"<a> nav item {text!r} looks disabled (opacity/cursor:default/disabled-class) "
                    "but has no onclick / functional href / data-page handler. "
                    "Either implement the target page or remove this item from nav."
                ),
            ))

    return issues


# ─── button no handler ───────────────────────────────────────────────────

def check_proto_button_no_handler(prototype: dict) -> list[Issue]:
    """Flag <button id="X"> with no onclick AND id never referenced in any inline
    <script>. Button without an id is excluded — class-only buttons may be wired
    via delegated event handlers we cannot reliably detect via regex.
    """
    issues: list[Issue] = []
    html = (prototype.get("prototype_html") or "")
    if not html:
        return issues
    scripts = "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", html, re.S | re.I))

    for m in re.finditer(r"<button\b([^>]*)>", html, re.I):
        attrs = m.group(1)
        if re.search(r"\bdisabled\b", attrs, re.I):
            continue
        if re.search(r"\bonclick\s*=", attrs, re.I):
            continue
        id_m = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', attrs)
        if not id_m:
            # class-only buttons skipped (may be delegated)
            continue
        bid = id_m.group(1)
        # Look for any reference of bid in scripts
        referenced = (
            f'"{bid}"' in scripts
            or f"'{bid}'" in scripts
            or f"#{bid}" in scripts
        )
        if not referenced:
            issues.append(Issue(
                step="prototype",
                category="prototype_button_no_handler",
                detail=(
                    f"<button id=\"{bid}\"> has no onclick attr and id is never referenced "
                    "in any inline <script> (no getElementById / querySelector / selector). "
                    "Button does nothing when clicked."
                ),
            ))
    return issues


# ─── default-open modal ──────────────────────────────────────────────────

def check_proto_default_open_modal(prototype: dict) -> list[Issue]:
    """Flag CSS rules whose selector contains 'modal' / 'popup' / 'help' AND
    declares both position:fixed and display:block (or other visible display)
    by default — overlays should default to display:none and open on user gesture.

    Rules inside @media or with .show / .open / .on modifier suffix are exempted.
    """
    issues: list[Issue] = []
    html = (prototype.get("prototype_html") or "")
    if not html:
        return issues
    css = _proto_extract_styles(html)
    if not css:
        return issues

    for sel, body in _proto_iter_css_rules(css):
        sel_l = sel.lower()
        # Match base modal selectors only (not state modifiers like .modal.show)
        if not re.search(r"\b(modal|popup|help-?modal|overlay)\b", sel_l):
            continue
        # State modifier? skip (.modal.show, .modal-mask.on, etc.)
        if re.search(r"\.(show|open|on|active|visible)\b", sel_l):
            continue
        if "position" not in body.lower() or not re.search(r"position\s*:\s*fixed", body, re.I):
            continue
        # default display: block / flex / grid (anything other than none)
        disp_m = re.search(r"\bdisplay\s*:\s*([\w-]+)", body, re.I)
        if not disp_m:
            continue
        disp = disp_m.group(1).lower()
        if disp == "none":
            continue
        issues.append(Issue(
            step="prototype",
            category="prototype_default_open_modal",
            detail=(
                f"selector '{sel[:80]}' is a position:fixed modal/overlay with "
                f"display:{disp} by default → blocks underlying UI on page load. "
                "Default should be display:none, opened by user gesture via a .show/.on modifier."
            ),
        ))
    return issues


# ─── admin responsive break ──────────────────────────────────────────────

# Match admin-specific selectors (not generic '.desktop' which is the desktop
# layout frame itself and intentionally fixed-width).
_PROTO_ADMIN_SEL_RE = re.compile(r"\b(adm-[\w-]*|dash-[\w-]*|dashboard[\w-]*)\b", re.I)


def check_proto_admin_responsive_break(prototype: dict) -> list[Issue]:
    """Flag admin-scoped CSS rules (selector contains adm-/dash-/dashboard) with
    fixed width:Npx where N > 412 (mobile breakpoint) AND not wrapped in any
    @media (min-width: ...) guard.

    Excludes generic '.desktop' and '.admin' top-level layout frames — those are
    intentional desktop-only containers (use admin_coverage check for those).
    """
    issues: list[Issue] = []
    html = (prototype.get("prototype_html") or "")
    if not html:
        return issues
    css = _proto_extract_styles(html)
    if not css:
        return issues
    # Strip @media (min-width:...) blocks — anything inside is guarded
    css_unguarded = re.sub(
        r"@media[^{]*\bmin-width\b[^{]*\{(?:[^{}]|\{[^{}]*\})*\}",
        "",
        css,
        flags=re.I | re.S,
    )

    for sel, body in _proto_iter_css_rules(css_unguarded):
        if not _PROTO_ADMIN_SEL_RE.search(sel):
            continue
        for wm in _PROTO_PX_WIDTH_RE.finditer(body):
            w = int(wm.group(1))
            if w > 412:
                issues.append(Issue(
                    step="prototype",
                    category="prototype_admin_responsive_break",
                    detail=(
                        f"admin selector '{sel[:80]}' declares width:{w}px (> 412px mobile "
                        "viewport) with no @media (min-width:...) guard. "
                        "Wrap in `@media (min-width: 768px) {{ ... }}` or use max-width."
                    ),
                ))
                break
    return issues


def check_prototype_help_step_coverage(spec_basic_data: dict, prototype_data: dict) -> list[Issue]:
    """proto-help 步驟陣列長度必須 == len(user_journey) + len(admin_journey
    OR admin wireframes count)。不准 AI 自己取捨步數。
    """
    import re
    html = (prototype_data.get("prototype_html") or "")
    uj_count = len(spec_basic_data.get("user_journey") or [])
    aj_count = len(spec_basic_data.get("admin_journey") or [])
    if aj_count == 0:
        # fall back to admin wireframes count
        aj_count = sum(1 for w in (spec_basic_data.get("wireframes") or [])
                       if ("後台" in w.get("name", "")) or ("admin" in w.get("name", "").lower()))
    expected = uj_count + aj_count
    if expected == 0:
        return []

    # Count <li> within proto-help block (most common skeleton)
    m = re.search(r'<[^>]*\bclass\s*=\s*["\'][^"\']*proto-help[^"\']*["\'][^>]*>(.*?)</div>', html, re.S)
    if not m:
        # Help block missing entirely
        return [Issue(
            step="prototype",
            category="prototype_help_steps_incomplete",
            detail=f"proto-help 區塊缺失。需要 {expected} 步（user_journey={uj_count} + admin={aj_count}）。",
        )]
    help_html = m.group(1)
    step_count = len(re.findall(r"<li\b", help_html))
    if step_count < expected:
        return [Issue(
            step="prototype",
            category="prototype_help_steps_incomplete",
            detail=(f"proto-help 只有 {step_count} 步，需要 {expected} 步"
                    f"（user_journey {uj_count} 步 + admin {aj_count} 步，1:1 對應）。"
                    f"請補回缺少的，不准壓縮玩家旅程或 admin 旅程。"),
        )]
    return []


# ─── 「舊功能必保留」守門 ───────────────────────────────────────
# 重生 step 時 baseline = 舊版 input.json 內容，current = 新版產出
# 任一可量化欄位 count < baseline → issue feature_count_regression
# 這是系統性守門：阻止 AI 為塞新需求悄悄削減舊功能項目。

_REGRESSION_PATHS_BY_STEP = {
    "spec-basic": [
        ("competitors", lambda d: len(d.get("competitors") or [])),
        ("axes", lambda d: len(d.get("axes") or [])),
        ("fields", lambda d: len(d.get("fields") or [])),
        ("user_journey", lambda d: len(d.get("user_journey") or [])),
        ("admin_journey", lambda d: len(d.get("admin_journey") or [])),
        ("ui_sections", lambda d: len(d.get("ui_sections") or [])),
        ("i18n", lambda d: len(d.get("i18n") or [])),
        ("help_page.steps", lambda d: len((d.get("help_page") or {}).get("steps") or [])),
        ("help_page.bullets", lambda d: len((d.get("help_page") or {}).get("bullets") or [])),
        ("timeline", lambda d: len(d.get("timeline") or [])),
        ("wireframes", lambda d: len(d.get("wireframes") or [])),
    ],
    "spec-advanced": [
        ("apis", lambda d: len(d.get("apis") or [])),
        ("data_models", lambda d: len(d.get("data_models") or [])),
        ("business_logic", lambda d: len(d.get("business_logic") or [])),
        ("cache_strategy", lambda d: len(d.get("cache_strategy") or [])),
        ("db_queries", lambda d: len(d.get("db_queries") or [])),
        ("redis_ops", lambda d: len(d.get("redis_ops") or [])),
    ],
    "assets": [
        ("assets", lambda d: len(d.get("assets") or [])),
    ],
    "bdd": [
        ("scenarios", lambda d: len(d.get("scenarios") or [])),
    ],
    "scrum": [
        ("stories", lambda d: len(d.get("stories") or [])),
    ],
    "docs": [
        ("sections", lambda d: len(d.get("sections") or [])),
        ("api_explorer", lambda d: len(d.get("api_explorer") or [])),
    ],
}


def check_no_regression(step_name: str, current: dict, baseline: dict | None) -> list[Issue]:
    """If a baseline (previous input.json) exists, ensure every quantifiable
    field in `current` has count >= baseline. Otherwise issue
    `feature_count_regression` so the fixer is forced to restore the cut content.
    """
    if not baseline:
        return []
    paths = _REGRESSION_PATHS_BY_STEP.get(step_name, [])
    issues: list[Issue] = []
    for path, getter in paths:
        was = getter(baseline)
        now = getter(current)
        if now < was:
            issues.append(Issue(
                step=step_name,
                category="feature_count_regression",
                detail=f"{path}: 之前有 {was} 個，現在剩 {now} 個。"
                       f"請補回缺少的（可以增加但不准減少 — 新需求不應擠掉舊內容）。",
            ))
    return issues


# ─── browser-based prototype layout audit (Playwright, optional) ──────

_PLAYWRIGHT_WARNED = False  # warn once per process

def check_proto_layout_via_browser(prototype: dict) -> list[Issue]:
    """Render prototype_html in headless chromium, detect ANY element where
    scrollWidth > clientWidth + 2 (horizontal layout overflow that browser
    actually exhibits — catches grid/flex sizing bugs static text analysis can't).

    Graceful degradation: if playwright not installed OR chromium binary
    missing → write one-line stderr warning, return [] (NOT a blocking issue).
    Pipeline continues with text-only checks.

    NO disk IO — uses page.set_content() to feed HTML string in-memory.
    """
    html = prototype.get("prototype_html") or ""
    if not html:
        return []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        global _PLAYWRIGHT_WARNED
        if not _PLAYWRIGHT_WARNED:
            import sys
            sys.stderr.write(
                "[warn] playwright not installed — prototype layout audit SKIPPED.\n"
                "       Install: pip install playwright && playwright install chromium\n"
            )
            _PLAYWRIGHT_WARNED = True
        return []

    issues: list[Issue] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            scenes = sorted(set(re.findall(r'scene-([a-z0-9_-]+)', html))) or [None]
            surfaces = sorted(set(re.findall(r'data-surface=["\']([^"\']+)["\']', html))) or [None]

            seen_keys = set()
            for viewport_w in (1440,):
                page = browser.new_page(viewport={"width": viewport_w, "height": 900})
                page.set_content(html, wait_until="load")
                page.wait_for_timeout(150)
                page.evaluate("document.querySelectorAll('[class*=\"help\"], [class*=\"intro\"]').forEach(e=>e.remove())")
                for surface in surfaces:
                    if surface is not None:
                        page.evaluate(
                            "(s) => document.querySelectorAll('[data-surface]').forEach(e => e.classList.toggle('on', e.dataset.surface===s))",
                            surface,
                        )
                    for scene in scenes:
                        if scene is not None:
                            page.evaluate(
                                "(s) => document.querySelectorAll('.phone').forEach(p => { p.className = p.className.replace(/scene-[a-z0-9_-]+/g, '').trim() + ' scene-' + s; })",
                                scene,
                            )
                            page.wait_for_timeout(80)
                        overflows = page.evaluate("""
() => {
  const out = [];
  document.querySelectorAll('*').forEach(el => {
    if (el.scrollWidth - el.clientWidth > 2) {
      const cs = getComputedStyle(el);
      out.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className||'').toString().slice(0,60),
        delta: el.scrollWidth - el.clientWidth,
        client: el.clientWidth,
        scroll: el.scrollWidth,
        clipped: ['hidden','clip'].includes(cs.overflowX),
      });
    }
  });
  return out;
}
                        """)
                        for o in overflows:
                            key = (o["cls"], o["delta"], viewport_w, surface, scene)
                            if key in seen_keys:
                                continue
                            seen_keys.add(key)
                            clip_note = " (CLIPPED by overflow-x:hidden)" if o["clipped"] else ""
                            label = f"viewport={viewport_w}px"
                            if surface: label += f" surface={surface}"
                            if scene:   label += f" scene={scene}"
                            issues.append(Issue(
                                step="prototype",
                                category="prototype_browser_overflow",
                                detail=(
                                    f"<{o['tag']} class='{o['cls']}'> scrollWidth={o['scroll']} > "
                                    f"clientWidth={o['client']} (+{o['delta']}px){clip_note} "
                                    f"at {label}"
                                ),
                            ))
                page.close()
            browser.close()
    except Exception as e:
        import sys
        sys.stderr.write(f"[warn] prototype layout audit failed ({type(e).__name__}: {e}) — SKIPPED.\n")
        return []
    return issues


def run_all_checks(step_name: str, all_step_data: dict, baseline: dict | None = None) -> list[Issue]:
    """Run every check whose target step matches `step_name` AND whose
    required upstream data is present. Returns the union of resulting Issues."""
    sb = all_step_data.get("spec-basic") or {}
    sa = all_step_data.get("spec-advanced") or {}
    assets = all_step_data.get("assets") or {}
    bdd = all_step_data.get("bdd") or {}

    issues: list[Issue] = []

    scrum = all_step_data.get("scrum") or {}

    if step_name == "assets" and sb and assets:
        # check_resource_counts (per-type total of nested subkeys) intentionally
        # NOT called — baseline sb uses nested subkeys as "spec/kind list" (each
        # =1) while assets count is instances, so sum != assets count by design.
        # The authoritative contract is the explicit bookkeeping totals.
        issues += check_assets_matches_sb_totals(sb, assets)

    if step_name == "bdd" and bdd:
        issues += check_scenario_count(bdd, sb, sa)

    if step_name == "scrum" and sb and scrum:
        # Scrum step owns per-role + total points checks + epic structure.
        issues += check_scrum_workload(sb, scrum, sa)
        issues += check_scrum_no_teams_field(scrum)
    if step_name == "spec-basic" and sb:
        # spec-basic 純自洽（不跨 doc）— 全部從 sb 自有 bookkeeping 算。
        issues += check_timeline_against_formula(sb)
        issues += check_admin_wireframe_dsl(sb)
        issues += check_admin_wireframe_self_consistency(sb)
        issues += check_wireframe_row_inline_only(sb)

    if step_name == "spec-advanced" and sa:
        issues += check_dryrun_vs_advanced(sb, sa)
        issues += check_sql_index_alignment(sa)
        issues += check_redis_key_alignment(sa)
        issues += check_apis_postman_grade(sa)

    if step_name == "prototype" and sb:
        proto = all_step_data.get("prototype") or {}
        if proto:
            issues += check_prototype_admin_coverage(sb, proto)
            issues += check_prototype_layout_skeleton(sb, proto)
            issues += check_prototype_help_step_coverage(sb, proto)
            # 5 new layout/UX guards — pure proto, no upstream needed
            issues += check_proto_horizontal_overflow(proto)
            issues += check_proto_dead_nav_item(proto)
            issues += check_proto_button_no_handler(proto)
            issues += check_proto_default_open_modal(proto)
            issues += check_proto_admin_responsive_break(proto)
            issues += check_proto_layout_via_browser(proto)

    # baseline regression check (system-wide; applies to every step)
    if baseline:
        current = all_step_data.get(step_name) or {}
        if current:
            issues += check_no_regression(step_name, current, baseline)

    return issues
