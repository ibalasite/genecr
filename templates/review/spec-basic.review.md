# spec-basic review rules

You review `spec-basic.input.json`. Apply each numbered rule. Cite the
real input field path in every issue. Use only the category tags in the
whitelist.

## RULES

### R1 — `template_noise`
Check: no field value is a placeholder string.
Fail when: any string field equals or contains `<...>` / "TBD" / "<待補>" / "<填寫>".

### R2 — `shallow_competitor`
Check: every entry in `competitors[]` has all required sub-fields filled
with concrete content (no placeholders, no one-word answers).
Path: `competitors[*].{name, market, highlight, url}` plus any extended
fields (mechanic, rtp, payout, user_flow, differentiation, weakness) the
input declares.
Fail when: any sub-field is empty, a placeholder, or one word.

### R3 — `count_inconsistent`
Check: `resource_counts.<category>` integer equals the number of entries
in this document that match that category.
Path: `resource_counts.*`
Fail when: declared count != actual count of matching entries within this
document (e.g. resource_counts.competitors=6 but competitors[] has 5).
Note: cross-document counts are checked by program cross_check, not here.

### R4 — `axis_option_mismatch`
Check: `matrix.cols` values appear as `options[].name` in some axis;
`matrix.rows[].label` values appear as `options[].name` in some axis.
Path: `matrix.{cols, rows[].label}` ↔ `axes[*].options[*].name`
Fail when: matrix references a label that no axis option defines.

### R5 — `journey_no_wireframe`
Check: every meaningful step in `user_journey[]` is depicted by at least
one `wireframes[]` entry.
Path: `user_journey[*]` ↔ `wireframes[*]`
Fail when: a journey step has no wireframe that visualises it.

### R6 — `i18n_missing`
Check: every translation key referenced in `ui_sections`, `ui_misc`, or
`copywriting` (if present) exists in `i18n` for every declared language.
Path: `i18n.*`
Fail when: a referenced key is missing for any declared language.

### R7 — `untestable_acceptance`
Check: every entry in `rules[]` (or `acceptance_criteria[]` if present)
specifies a concrete condition + observable outcome.
Path: `rules[*]` / `acceptance_criteria[*]`
Fail when: text is purely abstract ("system works", "good UX"), or
specifies an outcome without the triggering condition.

### R8 — `unresolved_reference`
Check: every cross-ID (e.g. `api-xxx`, `sc-xxx`, `ASSET-xxx`) referenced
inside this document resolves to another item in this document, or to
an upstream document.
Path: any string that matches the ID patterns
Fail when: ID appears but no definition is found.

### R9 — `skeleton_with_text`
Check: `.wf-skeleton-line` / `.wf-skeleton-pill` / `.wf-skeleton-block`
must be **empty placeholders** (LOADING state) — never contain text
content. Wireframe DSL section 3.6 is explicit.
Path: `wireframes[*].html`
Fail when: regex `class="[^"]*wf-skeleton-(line|pill|block)[^"]*"[^>]*>\s*[^<\s]` matches (skeleton tag has text content between open/close).
Fix hint: replace `.wf-skeleton-line` with `.wf-line` (text line) or `.wf-text` (paragraph).

### R10 — `inline_children_no_row`
Check: `.wf-panel` may not contain `<span>` children directly — inline
items must be wrapped in `.wf-row` for horizontal layout.
Path: `wireframes[*].html`
Fail when: regex `<div[^>]*class="[^"]*wf-panel[^"]*"[^>]*>\s*<span` matches.
Fix hint: wrap the inline children in `<div class="wf-row">…</div>`.

### R11 — `class_not_in_dsl`
Check: every `wf-*` class used in wireframe HTML must be declared in
`templates/wireframe-dsl.md` section 3 (no self-invented classes).
Path: `wireframes[*].html`
Fail when: a wf-* class string is not on the DSL allow-list.
Fix hint: pick a real DSL primitive; do not invent classes.

### R12 — `resource_counts_must_be_nested`
Check: `resource_counts` 中每個 asset 大類（image / sound / animation / video / particle / font / copywriting / ...）必須是 **nested dict** `{子類: int}`，不可給純整數總數。
Path: `resource_counts.*`
Fail when: 任一 asset 類別的值是 `int` 而非 `{子類: int}` dict。例外：`modules` / `acceptance_criteria` / `api_endpoints` 等 bookkeeping 欄位允許純整數。
Fix hint: 拆子類別，例如 `"image": 24` → `"image": {"格子狀態圖": 21, "寶箱": 1, "二選一卡片": 2}`。

### R_visual_audio_totals — `resource_counts_total_missing`
Check: `resource_counts.visual_total` 與 `resource_counts.audio_total` 必為整數且 >= 0。
Path: `resource_counts.visual_total` / `resource_counts.audio_total`
Fail when: 缺少或非整數。
Fix hint: 補上 AI 自報的「美術實體總數」（image+animation+particle+video+font 個別檔案數）與「音效檔總數」。下游 assets step 的 Counter(assets[].type) 必須對齊這兩個數字。

### R13 — `timeline_overestimated` / `timeline_underestimated`
Check: spec-basic 純自洽（不讀任何下游 sibling）。
**公式**（per-role budget，全從 sb 自有 bookkeeping）：
- art = 0.2 × sum(resource_counts art types)
- server = 1.0 × resource_counts.api_endpoints
- client = 0.67 × len(wireframes)
- planner = 0.2 × (len(user_journey) + len(admin_journey) + matrix.rows + 5)
- **total_weeks = ceil(max(per-role-days) / 5)**（無條件進位整數週）

Path: `timeline[*].duration_weeks` 總和
Fail when: total != expected（overestimated 標 `timeline_overestimated`、underestimated 標 `timeline_underestimated`）
Fix hint: cross_check.check_timeline_against_formula 程式算出，issue 含具體數字；調 phase 至 expected。
範例：8 api + 43 asset + 7 wf + 5 sect → max(8, 8.6, 4.69, 1)=8.6 day → ceil(8.6/5) = **2 週**

### R14 — `wireframe_admin_uncovered`
Check: every `/admin/`、`/internal/`、`/dashboard/`、`/console/` endpoint in
spec-advanced.apis has a matching `wireframes[]` entry whose name/desc
references the admin function (fuzzy match on the last path segment or
summary keyword).
Path: `wireframes[*].name/desc` ↔ `spec-advanced.apis[*].path`
Fail when: an admin/internal endpoint exists but no wireframe mentions it.
Fix hint: 加一條獨立 wireframe，name 包含「後台」或對應功能（如「後台 — 玩家記錄列表」）。
**禁止**把多個 admin 功能壓成一條「後台管理頁」。

### R15c — `admin_wireframe_missing_for_journey`
Check: if `admin_journey` non-empty, `wireframes[]` must contain at least
one entry whose name 含「後台」/`admin`.
Path: `wireframes[*].name` ↔ `admin_journey`
Fail when: admin_journey exists but no admin wireframe to demo it.
Fix hint: 加一條 wireframe，name 含「後台」+ 對應功能。

### R15b — `admin_journey_missing`
Check: if any `wireframes[].name` contains 「後台」/`admin`, `admin_journey`
must be a non-empty array.
Path: `admin_journey` ↔ `wireframes[*].name`
Fail when: admin wireframe exists but admin_journey is missing or empty.
Fix hint: 加 `admin_journey: [{"action":"建立活動","detail":"…","role":"admin"}, …]`，
每一步對應一個後台操作；下游 prototype 用 admin_journey.length + user_journey.length
決定「下一步」總步數，不可省略。

### R15 — `wireframe_scrum_story_uncovered`
Check: every `scrum.stories[]` whose title/description contains UI keywords
(「UI」/「介面」/「面板」/「列表」/「畫面」/「dashboard」/「console」) has
at least one matching `wireframes[]` entry covering the same surface.
Path: `wireframes[*].name` ↔ `scrum.stories[*].title`
Fail when: a UI-implying story has no covering wireframe.

### R16 — `admin_wireframe_wrong_container`
Check: every wireframe with `name` containing 「後台」/`admin` must use
`wf-desktop` (or `wf-desktop-app` with sidebar) as its container, NOT
`wf-frame` (mobile/通用窄欄).
Path: `wireframes[*].html`
Fail when: admin wireframe html lacks `wf-desktop` keyword.
Fix hint: 把 `<div class="wf-frame">` 換成 `<div class="wf-desktop">`，
單面用 `wf-desktop`、含 sidebar 用 `wf-desktop-app`。

### R17 — `admin_form_uses_skeleton_pill`
Check: admin wireframe html must NOT contain `wf-skeleton-pill`. That class
is a shimmer loading placeholder, not a form input.
Path: `wireframes[*].html`
Fail when: admin wireframe contains `wf-skeleton-pill`.
Fix hint: 改用 `<input class="wf-input">` / `<input class="wf-input-date">` /
`<select class="wf-select">` / `<textarea class="wf-textarea">`，配
`wf-form-row` 標籤對。

### R18 — `admin_table_uses_pills`
Check: admin wireframe must use `wf-table > wf-tr > wf-td` for tabular data.
Pill rows (≥ 4 `wf-pill` in one `wf-row`) faking tables are forbidden.
Path: `wireframes[*].html`
Fail when: admin wireframe has a wf-row with 4+ wf-pill children but no wf-table.
Fix hint: 改用 `<div class="wf-table"><div class="wf-tr"><div class="wf-td">玩家ID</div>…</div>…</div>`，
搭配 `wf-toolbar`（上方搜尋）跟 `wf-pagination`（分頁）。

## ISSUE CATEGORY TAGS (whitelist — emit ONLY these)

- `template_noise`
- `shallow_competitor`
- `count_inconsistent`
- `axis_option_mismatch`
- `journey_no_wireframe`
- `i18n_missing`
- `untestable_acceptance`
- `unresolved_reference`
- `skeleton_with_text`
- `inline_children_no_row`
- `class_not_in_dsl`
- `resource_counts_must_be_nested`
- `resource_counts_total_missing`
- `timeline_overestimated`
- `timeline_underestimated`
- `wireframe_admin_uncovered`
- `wireframe_scrum_story_uncovered`
- `admin_journey_missing`
- `admin_wireframe_missing_for_journey`
- `admin_wireframe_wrong_container`
- `admin_form_uses_skeleton_pill`
- `admin_table_uses_pills`
- `wireframe_row_contains_block`

### R_wf_row_inline — `wireframe_row_contains_block`
Check: 任一 wireframe `wf-row` 的直接 children 必須是 inline DSL primitives
(`wf-pill` / `wf-tag` / `wf-btn` / `wf-link` / `wf-icon` / `wf-line` /
`wf-helper` / `wf-input` / `wf-select` / `wf-checkbox` / `wf-radio` /
`wf-countdown` / `wf-section-title` / `wf-text` / `wf-skeleton-pill` /
`wf-skeleton-line` / `wf-dot`)。
**禁止** block primitive (`wf-panel` / `wf-card` / `wf-board` / `wf-stage` /
`wf-banner` / `wf-table` / `wf-cards-grid` / `wf-stat-card` 等) 當 wf-row
直接 child — 會撐爆 mobile/desktop frame 寬度。違規 emit
`wireframe_row_contains_block`。
Path: `wireframes[*].html`
Fail when: 任一 wf-row 元素直接 child 帶有 block class（wf-modal 子樹除外，
modal 自有寬度合法允許 side-by-side 選擇 wf-panel）。
Fix hint: 想做格子網格用 `<span class="wf-pill">…</span>` 排成多個 wf-row；
想堆 panel 用 `wf-stage` 直接包多個 `wf-panel` 縱向疊放，不要塞 wf-row。
