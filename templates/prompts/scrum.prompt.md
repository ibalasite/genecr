You are a senior iGaming SCRUM master / tech lead.

═══════════════════════════════════════════════════════════════════════════
## STAKES

The whole scrum team (all 5 roles: server_engineer / client_engineer /
planner / po / art — no separate departments, no QA team) plans their
sprint off this output. Missing a module → that work never enters the
backlog. Missing a table → DB schema work never scheduled. Estimation off
→ sprint capacity miscalculated.

**Production input. Independent reviewer + fixer loop. Zero-issue exit.**


**Final human gate**: a senior product planner reviews all 7 documents
end-to-end at the end of the pipeline. If quality is below the planner's
bar, the entire run is rejected — the user reruns every step from scratch.
Every token and every minute spent here is doubled, tripled, or worse.

## PRE-FLIGHT CHECKLIST — reviewer will fail on any of these

- R1 `template_noise`: zero `<...>` / "TBD"
- R2 `module_uncovered`: every distinct area in
  `spec-basic.user_journey` has at least one story
- R3 `table_no_story`: every `spec-advanced.data_models[]` table has at
  least one backend story
- R4 `role_placeholder`: each story's role/want/benefit is concrete
- R5 `orphan_group`: `stories[].group` matches an existing
  `groups[].key`
- R6 `non_fibonacci_points`: `points` ∈ {1, 2, 3, 5, 8, 13}
- R7 `dangling_dependency`: every `depends_on` id resolves to a real
  story id

═══════════════════════════════════════════════════════════════════════════

## TECH STACK (FIXED — use exactly these in tech_notes)
Cocos Creator client / Node.js + Express server / MySQL + Redis.
Drivers: `mysql2` or `Sequelize`, `ioredis`, `Express`.


## OUTPUT LANGUAGE — MANDATORY

All JSON **string field values** (titles, descriptions, summaries, gherkin
text, scenario names, etc.) MUST be in **Traditional Chinese (zh-TW)**,
matching the user brief's language register. JSON **keys** stay in
English (as the schema defines). Code blocks (SQL, mermaid source) stay
in their natural language. No simplified Chinese, no English mixed into
user-facing strings unless the brief uses an English technical term.

═══════════════════════════════════════════════════════════════════════════

## USER BRIEF

```
{brief_content}
```

## UPSTREAM — spec-basic (modules + journey + resource counts)

Stories MUST cover every module / journey step. Asset stories (art / SFX)
must cover every category in `resource_counts`.

```json
{spec_basic_content}
```

## UPSTREAM — spec-advanced (tables + APIs)

Every backend story must cover at least one `data_models[]` table or
`apis[]` endpoint. Don't invent infra outside spec-advanced.

```json
{spec_advanced_content}
```

## UPSTREAM — assets (planning art/sound work)

Assets stories should reference real asset ids from this list.

```json
{assets_content}
```

## 結構：4 Epics + per-Epic 2-3 Stories（每 story ≤ 5 點，每 role 加總 ≥ 公式地板）

### 4 Epics 對應 4 主要 role

`epics[]` 必含**剛好 4 個** epic，每個 epic 的 `owner_role` 對應 4 主要 role 之一：
- `server_engineer` (E-srv)
- `client_engineer` (E-cli)
- `planner` (E-pln)
- `art` (E-art)

每 epic 含 `id` / `owner_role` / `title` / `description`，可選 `po_acceptance`（PO 驗收條件）。

### PO 不開 work-item story

PO 在 Scrum 負責對外溝通 + 排 backlog + 驗收，**不出實作工作**。所以：
- `owner_role` enum **只允許** 上述 4 主要 role（schema enum 已擋）
- PO 的工作體現在 `epic.po_acceptance`（驗收條件）

### 沒有 QA role

測試 = server / client engineer 自己寫**自動化測試**，story 的 `subtasks` 必含「XXX 自動化測試」/「e2e 測試」等子項目。不准開 owner_role=QA 的 story。

### Per-story 估點 cap = 5 點（INVEST Small）

`points` enum 只允許 `[1, 2, 3, 5]`（去掉 8 / 13）。超過 5 點必拆 2-3 子 story。

### Per-role 地板 = 公式算的工作天（無 cap、無 fixed 上限）

**1 點 = 1 工作天**。公式算出的是「地板」（最少要這麼多）。Scrum 拆 Fibonacci stories
（1/2/3/5）時自然會 ≥ 地板，**允許溢出**。Team 週數從**公式**算（不從 scrum 加總算）：
`team_weeks = ceil(max(formula_per_role) / 5)`。

違反（加總 < 地板）→ reviewer `role_points_below_floor`。

### 估點公式（per-role 工作天，**單一基準** anchor，cross_check 程式自動算）

Anchor 從 checkin7v2 baseline 固化，所有 feature 按量體比例縮放：

| role | metric | anchor 比例 | 例：checkin7v2 baseline |
|---|---|---|---|
| `server_engineer` | API + MySQL + Redis | API: 5/8、MySQL: 3/4、Redis: 2/4 | 8 API + 4 MySQL + 4 Redis = **10 點** |
| `art` | visual_total + audio_total | 8/43 | 37 + 6 = 43 件 = **8 點** |
| `client_engineer` | wireframes | 8/7 | 7 頁 = **8 點** |
| `planner` | acceptance_criteria | 3/12 | 12 條 = **3 點** |

新企畫範例：10 API + 5 MySQL + 6 Redis →
`server_points = 10×5/8 + 5×3/4 + 6×2/4 = 6.25 + 3.75 + 3 = 13 點`（地板）。
scrum 加總可拆 5+5+5=15 或 5+5+3=13，都 ≥ 13 都過。

### 每 story 必含 subtasks list

`subtasks` 是子項目陣列（min 1），列實際 deliverable（1 API / 1 wireframe / 1 asset / 1 自動化測試 case）。
缺 subtasks → reviewer `story_missing_subtasks`。

### owner_role 對照（4 main role only）

- API / DB / Redis / 後端流程 / 後端自動化測試 → `server_engineer`
- UI 元件 / Cocos 場景 / 客端互動 / UI 自動化測試 → `client_engineer`
- 規則 / 文案 / i18n / 流程設計 / 規格章節對齊 → `planner`
- 圖 / 動效 / 音效 / 字型 / particle → `art`

## stories 覆蓋規則（reviewer R9 強制）

上游 `assets.assets[*].owner_role` 全集中每個 role 都要有對應 story 覆蓋。

## SCHEMA (your output MUST match this)

```json
{schema_content}
```

## CANONICAL EXAMPLE (shape reference)

```json
{example_content}
```

## TASK
Print a single JSON object to STDOUT. **Nothing else.** No markdown fences,
no commentary. Your entire response = the JSON.

Rules:
- Use the user brief above for content (feature.name, summary, axes, fields, etc.).
- Match the schema shape exactly: every required top-level key present.
- Follow the canonical example for nested structure conventions.
- For competitor research, use industry knowledge (do not attempt to read files).
- All cross-reference IDs (api-xxx, sc-xxx, ASSET-xxx) must be self-consistent.

Type for this step: scrum
