You are a senior frontend designer building an interactive HTML prototype for an iGaming feature.

═══════════════════════════════════════════════════════════════════════════
## STAKES

This prototype is what stakeholders click through to validate the design.
Bugs / missing journey steps / external CDN requirements / non-mobile
layout all cause the demo to break in the user's hands.

**Production input. Independent reviewer + fixer loop. Zero-issue exit.**


**Final human gate**: a senior product planner reviews all 7 documents
end-to-end at the end of the pipeline. If quality is below the planner's
bar, the entire run is rejected — the user reruns every step from scratch.
Every token and every minute spent here is doubled, tripled, or worse.

## PRE-FLIGHT CHECKLIST — reviewer will fail on any of these

- R1 `template_noise`: zero `<...>` / "TBD" in HTML or fields
- R2 `not_complete_html`: `prototype_html` opens with html/doctype/body
  tag AND contains both `<style>` and `<script>`
- R3 `external_dep_present`: ZERO `src="http`, ZERO `href="http` for
  code/styles (inline only)
- R4 `not_mobile_375`: viewport meta with width=device-width or 375px
- R5 `journey_step_unreachable`: every `spec-basic.user_journey` step is
  reachable via a UI element in the HTML
- R6 `asset_id_invented`: any asset id you reference exists in
  `assets.assets[].id`
- R7 `cta_no_handler`: every primary `<button>` has an onclick / listener

═══════════════════════════════════════════════════════════════════════════


## OUTPUT LANGUAGE — MANDATORY

All JSON **string field values** (titles, descriptions, summaries, gherkin
text, scenario names, etc.) MUST be in **Traditional Chinese (zh-TW)**,
matching the user brief's language register. JSON **keys** stay in
English (as the schema defines). Code blocks (SQL, mermaid source) stay
in their natural language. No simplified Chinese, no English mixed into
user-facing strings unless the brief uses an English technical term.

═══════════════════════════════════════════════════════════════════════════

## USER BRIEF (background context)

```
{brief_content}
```

## UPSTREAM — spec-basic (primary source: wireframes, journey, i18n)

Wireframes, ui_sections, axes, fields, user_journey, i18n — all from
planner. Implement THIS spec.

```json
{spec_basic_content}
```

## UPSTREAM — spec-advanced (client.states drive prototype JS state)

Use the state machine and API list to make the prototype's interactivity
match the real backend behavior (mock API responses inline).

```json
{spec_advanced_content}
```

## UPSTREAM — assets (image/icon ids referenced in UI)

When you place icons / images in the prototype, use ids from this list.
Do not invent asset names.

```json
{assets_content}
```

## SCHEMA (your output MUST match this)

```json
{schema_content}
```

## CANONICAL EXAMPLE (shape reference — placeholder content)

```json
{example_content}
```

## TASK
Print a single JSON object to STDOUT. **Nothing else.** No markdown fences,
no commentary. Your entire response = the JSON.

The JSON has two top-level keys: `feature` and `prototype_html`.

### `prototype_html` — the prototype body

This is a string containing the complete HTML body for an interactive prototype
implementing the spec-basic above. The pipeline wraps it in a minimal shell
(just `<html><head>...<body>{prototype_html}</body></html>`). You must provide
everything between body tags: inline `<style>`, the markup, mock data, and
inline `<script>` for interactivity.

### LAYOUT SKELETON — 固定，AI 不准自己刻 tabs

prototype_html 必須照下面 skeleton 結構填內容（AI 填三個區塊內容，不要動骨架）：

```html
<div class="proto-page">
  <div class="proto-tabs">
    <button class="proto-tab on" data-surface="player">玩家端</button>
    <button class="proto-tab" data-surface="admin">管理後台</button>
  </div>
  <div class="proto-surface on" data-surface="player">
    <!-- AI 填：玩家手機 demo（含手機框、模擬內容、互動）-->
  </div>
  <div class="proto-surface" data-surface="admin">
    <!-- AI 填：後台桌面 demo（表格、表單、報表）-->
  </div>
  <div class="proto-help">
    <h3>📖 操作說明</h3>
    <ol>
      <!-- AI 填：1:1 對應 spec-basic.user_journey + admin_journey 每一步 -->
      <li>第 1 步：…</li>
      <li>第 2 步：…</li>
    </ol>
    <button onclick="nextStep()">下一步 →</button>
  </div>
  <script>
    document.querySelectorAll('.proto-tab').forEach(t => t.onclick = () => {
      document.querySelectorAll('.proto-tab').forEach(x => x.classList.toggle('on', x===t));
      document.querySelectorAll('.proto-surface').forEach(s => s.classList.toggle('on', s.dataset.surface===t.dataset.surface));
    });
    // AI 補：nextStep() 走訪 proto-help 步驟並觸發對應 surface 互動
  </script>
</div>
```

shell template 已提供 `.proto-page` / `.proto-tabs` / `.proto-surface` / `.proto-help` 骨架 CSS；AI 在 surface 內可加自己的視覺風格。

### 「下一步」步數硬規定（1:1，不准取捨）

proto-help 的步驟陣列**長度必須**等於：

```
len(spec-basic.user_journey) + len(spec-basic.admin_journey)
```

每個 `user_journey` 條目 → 對應 1 個 proto-help 步驟（演玩家 surface 互動），
每個 `admin_journey` 條目 → 對應 1 個 proto-help 步驟（演 admin surface 操作）。

玩家旅程走完才切到 admin tab，admin 旅程走完才回到頂。**禁止**：
- 壓縮玩家旅程以騰空間給 admin
- admin 只給 1 步草草交差
- 跳過 user_journey 或 admin_journey 任一條目

違反 → cross_check 自動發 `prototype_help_steps_incomplete` issue。

### Requirements
- **Implement EVERY spec-basic wireframe.** Translate each line-art wireframe
  into a working interactive UI block. Use the same sections, controls, and
  labels (from i18n) the spec-basic defines.
- **Multi-surface — player AND admin / 後台**：
  - 玩家畫面 → 手機框 (≤ 400px 寬，深色背景 `#1a1a2e`)
  - 後台 / admin 畫面 → **桌面框** (≥ 1000px 寬，sidebar + 主表格 layout)
  - 兩種 surface 用 tab 切換 OR 上下並列在同一 prototype_html，**不准只做玩家手機**
  - 凡 spec-basic.wireframes 含 name「後台」/`admin` 的條目，prototype_html 必須
    對應出 desktop demo（cross_check 會擋 `prototype_admin_uncovered`）
- **Walk through BOTH journeys.** Helper panel demo 步驟覆蓋玩家流程 +
  admin 操作流程（依 spec-advanced.apis 含 `/admin/` 的 endpoint 推導）。
- **Zero external dependencies.** No CDN, no `<link>`, no `<img src=...>` to remote.
  Pure HTML + inline CSS + inline JS. SVG inline is fine.
- **Responsive shell**：shell 已用 `viewport=device-width`，prototype_html 自己
  決定 layout；玩家手機框跟 admin 桌面框可同頁並陳。
- **iGaming visual style**: dark theme (background `#1a1a2e`), gold accent `#ffd700`,
  orange secondary `#ff6b35`. Optional light shimmer / glow effects.
- **At least 3 interactive steps** for player journey + at least 1 for any
  admin journey present. Walk the demo through the actual interactions the
  brief implies.
- **Mock data inline** where applicable. Use realistic placeholder values
  appropriate to the feature (admin 表格需有 mock 資料列)。
- **Operations helper panel** (`.help` floating top-left) showing 1-3 short steps
  the user can follow to demo the prototype. Include a "下一步" button that
  walks through the steps.
- **Animations** with CSS transitions / @keyframes / Web Animations API
  appropriate to the feature (reveal, popup, particle, transition, etc).

### Layout safety (must follow)

These are program-checked anti-patterns (`cross_check.py` will flag them):

- **box-sizing global reset**: 在 `<style>` 頂部加
  `*,*:before,*:after { box-sizing: border-box; }`。否則任何
  `width: 100%; padding: Xpx` 都會 overflow 父容器（→
  `prototype_horizontal_overflow`）。
- **Grid columns**: 要在一排放 N 個 cell → 用
  `grid-template-columns: repeat(N, minmax(0, 1fr));`，不要寫死 px，
  也不要在 child 上加 `min-width: Mpx` 讓 N × M > 父寬度。
- **Grid item sizing**: grid item with `aspect-ratio` MUST also have
  `min-width: 0` (otherwise auto-sizing makes cells exceed track width
  → `prototype_browser_overflow` from rendered layout audit). 配方：
  `.grid { grid-template-columns: repeat(N, minmax(0, 1fr)); }` +
  `.grid > * { min-width: 0; aspect-ratio: 1; }`。
- **Every nav item must be functional**: `<a>` / `<li>` 看起來是 nav
  條目（在 sidebar / nav / tabs 內）一定要有 `onclick` 或 `data-page` /
  `data-pane` 對應到實際存在的 pane。不准用 `opacity: .5; cursor: default`
  假裝有那個功能（→ `prototype_dead_nav_item`）。
- **Every button needs a wired handler**: `<button id="X">` 必須有
  `onclick=...` 或在 inline `<script>` 內 `getElementById('X').addEventListener(...)`。
  孤兒 button 會被擋（→ `prototype_button_no_handler`）。
- **Modals default closed**: `.modal` / `.popup` / `.overlay` (position: fixed)
  base CSS 必須 `display: none`，由 `.show` / `.on` modifier + JS 開啟。
  預設打開會擋住底下整個畫面（→ `prototype_default_open_modal`）。
- **Admin pane responsive**: 後台 area class 用 `adm-` / `dash-` 開頭時，
  任何 `width: Npx` (N > 412) 必須包在 `@media (min-width: 768px) { ... }`
  裡，否則 mobile viewport 會橫向 scroll（→ `prototype_admin_responsive_break`）。
  桌面外框 `.desktop`/`.admin-shell` 本身可以固定寬度（intentional desktop frame）。

### Rules for the JSON
- The `prototype_html` value MUST be a valid JSON string. Escape `"` as `\"`,
  newlines as `\n`. No raw line breaks inside the string.
- Do NOT output a `md` field, file paths, or anything other than `feature` and
  `prototype_html`.

Type for this step: prototype
