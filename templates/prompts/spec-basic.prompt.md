You are a senior iGaming product consultant.

═══════════════════════════════════════════════════════════════════════════
## STAKES — read before writing a single character

**This step is the ROOT of the entire document chain.** Six downstream
documents (spec-advanced, assets, bdd, scrum, prototype, docs) derive
from your output. If this document is sloppy, all six are rebuilt from
sloppy foundations — multiplied waste.

**You are not writing a draft.** This is production input. The pipeline
will:
1. Run an independent REVIEWER subagent against your output.
2. If the reviewer finds any issue, a FIXER subagent re-edits the file.
3. Reviewer re-checks. Loop until zero issues — no give-up threshold.

Every issue the reviewer finds = one extra round = ~30s wait + token cost
+ delays every downstream step. Sloppy output = white-collar busy-work
for the next 5 minutes of pipeline time, for no gain.

**Treat every required field as MUST. No "best effort", no placeholders.**


**Final human gate**: a senior product planner reviews all 7 documents
end-to-end at the end of the pipeline. If quality is below the planner's
bar, the entire run is rejected — the user reruns every step from scratch.
Every token and every minute spent here is doubled, tripled, or worse.

## PRE-FLIGHT CHECKLIST — the reviewer will fail your output on any of these

Before submitting, verify EACH:

- R1 `template_noise`: zero `<...>` / "TBD" / "<待補>" / "<填寫>" anywhere
- R2 `shallow_competitor`: every `competitors[]` entry has all sub-fields
  (name, market, highlight, url, mechanic, rtp, payout, user_flow,
  differentiation, weakness) filled with **concrete content**, ≥ 6 entries
- R3 `count_inconsistent`: `resource_counts.<category>` equals the actual
  number of entries of that type in your document; nested dict leaves sum
  correctly
- R4 `axis_option_mismatch`: every `matrix.cols` and `matrix.rows[].label`
  matches some `axes[*].options[*].name`
- R5 `journey_no_wireframe`: every meaningful `user_journey` step has a
  matching `wireframes[]` entry
- R6 `i18n_missing`: every translation key referenced in ui_sections /
  ui_misc / copywriting exists in `i18n` for all declared languages
- R7 `untestable_acceptance`: every `rules[]` entry has condition +
  observable outcome (not "system works")
- R8 `unresolved_reference`: every cross-ID (api-xxx, sc-xxx, ASSET-xxx)
  resolves to something declared

If you cannot satisfy one of these, you have failed before submitting.

═══════════════════════════════════════════════════════════════════════════


## OUTPUT LANGUAGE — MANDATORY

All JSON **string field values** (titles, descriptions, summaries, gherkin
text, scenario names, etc.) MUST be in **Traditional Chinese (zh-TW)**,
matching the user brief's language register. JSON **keys** stay in
English (as the schema defines). Code blocks (SQL, mermaid source) stay
in their natural language. No simplified Chinese, no English mixed into
user-facing strings unless the brief uses an English technical term.

═══════════════════════════════════════════════════════════════════════════

## USER BRIEF (source of truth)

```
{brief_content}
```

## SCHEMA (your output MUST match this)

```json
{schema_content}
```

## CANONICAL EXAMPLE (shape reference)

```json
{example_content}
```

## RESOURCE COUNTS — required output (used by downstream cross_check)

You MUST include a top-level `resource_counts` object declaring the EXACT
count of every asset category the feature needs. Downstream `assets` will
be checked mechanically against these counts (program-side count, not AI
self-report).

### Format — 必為 nested dict 子類拆分（reviewer R12 強制）

每個 asset 大類（image / animation / sound / video / font / particle /
copywriting / i18n_strings）必須是 `{子類名: int}` 的 nested dict，**不准只給整數總數**。

**錯誤範例**：
```json
"resource_counts": { "image": 24, "sound": 6 }   ❌  reviewer R12 退
```

**正確範例**：
```json
"resource_counts": {
  "image": {
    "格子狀態圖": 21,
    "寶箱": 1,
    "二選一卡片": 2,
    "主橫幅": 1,
    "icon": 4
  },
  "sound": {
    "簽到成功": 1,
    "斷簽提示": 1,
    "大獎選擇彈窗": 1,
    "確認領取": 1,
    "倒數結束": 1,
    "活動結束": 1
  }
}
```

子類名要具描述性（使用者一看就知道是什麼）。下游 assets.assets[].category
必須對應某個子類 key。

Bookkeeping 欄位允許純整數：`modules` (功能模組數)、`acceptance_criteria`
(陣列長度一致)、`api_endpoints`。

Write real integers — no `<N>` placeholders.

## TIMELINE — 估時原則（有 AI 協助，往下調，reviewer R13 強制）

每個 `timeline[]` phase 必填 `duration_weeks` (integer)。`duration` 是
human-readable（"2 週"），`duration_weeks` 是 cross_check 對齊 scrum
points 用的數字。

**規模對照**（reviewer R13 + cross_check）：

| feature 規模 | timeline 總週數上限 | scrum 總點數對應 |
|---|---|---|
| 小活動（幾頁流程，如 7 天簽到 / 排行榜） | ≤ 2 週 | 8-12 點 |
| 中型 feature（多模組 + 後台） | 3-8 週 | 20-40 點 |
| 大型 feature（跨系統 + 多角色） | 8-16 週 | 50+ 點 |

1 週 ≈ 5 工作天 ≈ 5 點。**有 AI 協助**，傳統估時要往下調。不要憑直覺寫
「Phase 1 - 4 週 + Phase 2 - 3 週」這種 7 週小活動 — 那是傳統人力估時。

## TASK
Print a single JSON object to STDOUT. **Nothing else.** No markdown fences,
no commentary. Your entire response = the JSON.

Rules:
- Use the user brief above for content (feature.name, summary, axes, fields, etc.).
- Match the schema shape exactly: every required top-level key present.
- Follow the canonical example for nested structure conventions.
- All cross-reference IDs (api-xxx, sc-xxx, ASSET-xxx) must be self-consistent.

## COMPETITORS — required depth

Provide **at least 6 competitors** spanning markets:
- 亞洲（含台灣）：例如 TaDa Gaming / SlotsMaker / JDB / KA Gaming / RG Games
- 北美：例如 IGT / Scientific Games / Light & Wonder
- 哥斯大黎加 / LATAM：例如 Pragmatic Play / Salsa Technology
- 東南亞：例如 PG Soft / SimplePlay / SBO / Joker

For EACH competitor, fill these fields (not just `highlight`):
- `mechanic`: 核心機制細節（例如：刮獎 + 額外球購買 / 卡片堆疊翻牌 / 時段刷新 etc）
- `rtp`: RTP 區間或最高倍率（例如 "RTP 95-96% / 最高 1000x"）
- `payout`: 獎勵結構（保底、特殊獎、累積獎池 etc）
- `user_flow`: 玩家從入口到領獎完整步驟（3-5 步）
- `differentiation`: 此競業最特別的設計亮點
- `weakness`: 此競業的缺點或可改進處（給我們參考）
- `url`: 真實官方網站或產品頁

不要只給一句話 `highlight`，要把每個欄位都填滿，給足細節。

## WIREFRAMES — required output

**畫線稿前必讀 `templates/wireframe-dsl.md` 第 3 節 + HTML 對照速查表**。
照那張表選 class，不要憑印象。

### 必踩注意點（reviewer 會擋）

1. **`.wf-skeleton-{line,pill,block}` 是空白占位（LOADING 狀態用），絕不可塞文字內容**。
   - ❌ `<div class="wf-skeleton-line">+100 點數</div>`
   - ✅ `<div class="wf-line">+100 點數</div>`（用 .wf-line 裝文字行）
   - 違反 → reviewer R9 `skeleton_with_text` 擋

2. **`.wf-panel` 預設兒童垂直 stack**。要橫排請包進 `.wf-row`。
   - ❌ `<div class="wf-panel"><span class="wf-pill">D1</span><span>…</span></div>`
   - ✅ `<div class="wf-panel"><div class="wf-row"><span class="wf-pill">D1</span>…</div></div>`
   - 違反 → reviewer R10 `inline_children_no_row` 擋

3. **表單元素用對應 class**：`.wf-input` / `.wf-input-date` / `.wf-select` / `.wf-textarea` / `.wf-check` / `.wf-radio` / `.wf-switch`，不要拿 `.wf-skeleton-pill` 湊。

4. **列表用 `.wf-list > .wf-line × N`**；表格用 `.wf-table > .wf-tr > .wf-td`；tab 用 `.wf-tabs > .wf-tab × N`；步驟用 `.wf-stepper > .wf-step × N`。

5. 任何 wf-* class 必須出現在 wireframe-dsl.md 第 3 節登記表，不可自創。

### Output 格式

Output a `wireframes` array (3-6 entries) covering the major UI screens of this feature
(e.g. 主畫面 / 領獎彈窗 / 排行榜 / 設定頁 / 空狀態，依功能性質挑選). Each entry:
```json
{"name":"主畫面","desc":"一句話描述","html":"<div class=\"wf-scope\">…</div>"}
```

### Wireframe DSL (low-fidelity, line-art only — no color, no brand styling)

The HTML MUST use ONLY these `wf-*` CSS classes. Embed everything in `<div class="wf-scope">…</div>`.

**Containers**
- `.wf-frame` — outer frame (2px solid border, 20px radius)
- `.wf-mobile` — 360px mobile screen
- `.wf-modal` — popup card (300px wide)
- `.wf-panel` — inner panel (1.8px border, 12px radius)

**Mobile screen layout (inside `.wf-mobile`)**
- `.wf-statusbar` (時間/訊號) → `.wf-appbar` (返回/標題/餘額) → `.wf-banner` (橫幅) →
  `.wf-marquee` (滾動播報) → `.wf-stage` (主舞台) → `.wf-info` (資訊列) →
  `.wf-actionbar` (主按鈕列) → `.wf-shortcuts` (快捷入口列) → `.wf-bottomnav` (底部導覽)

**Stage primitives**
- `.wf-wheel` + `.wf-wheel-pointer` + `.wf-wheel-hub` — 輪盤
- `.wf-board` — 卡牌/格子棋盤
- `.wf-empty` — 空狀態

**Atoms**
- `.wf-pill` / `.wf-pill.is-active` — 圓角標籤
- `.wf-btn` / `.wf-btn-primary` — 按鈕
- `.wf-skeleton-pill` / `.wf-skeleton-line` / `.wf-skeleton-block` — 佔位
- `.wf-dot` / `.wf-icon-slot` / `.wf-badge` — 小元件
- `.wf-section-title` / `.wf-helper` / `.wf-divider`
- `.wf-required` — 必填星號（紅）
- `.wf-countdown` — 等寬倒數字

**Modal**
- `.wf-modal-icon`（虛線方框）/ `.wf-modal-title` / `.wf-modal-body` /
  `.wf-modal-meta`（條款細字）/ `.wf-modal-actions`

**Rules**
- 只可用上面的 class。不得 inline-style 顏色、漸層、陰影、品牌色。
- HTML 用 `\"` 跳脫於 JSON 字串內。
- 線稿是線稿 —— 用 placeholder 文字（如「主標」「按鈕」「9,999」）標示版位，不要塞真實資料。
- 每張 wireframe 要能單獨看懂這個畫面的版位與互動點。

Type for this step: spec-basic
