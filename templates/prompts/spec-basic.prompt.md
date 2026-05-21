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
- R3 `count_inconsistent`: `dryrun.resource_counts.<category>` equals the actual
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
- R9 `dryrun_missing`: `dryrun.tech_counts` 三個欄位（api_endpoints / db_tables /
  redis_keys）必須是整數 ≥ 0，且 api_endpoints ≥ 3、db_tables ≥ 5（iGaming 底限）

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

**美術資源（image/animation/sound/video/font/particle）和 visual_total/audio_total
填在 `dryrun.resource_counts`。**
`dryrun.test_counts.acceptance_criteria` 填 `len(acceptance_criteria[])` 整數。

### dryrun.resource_counts.visual_total / audio_total（必填整數）

`dryrun.resource_counts` 必須包含 `visual_total` (整數) 與 `audio_total` (整數)。
- `visual_total` = 美術實體總數（image + animation + particle + video + font 你預期會交付的個別檔案數，例如 7 個 D-day 格子圖算 7 不是 1 種規格）。
- `audio_total` = 音效檔總數（sound 的個別檔案數）。

這兩個數字下游 assets step 必須對齊（`Counter(assets[].type)` 美術類加總 == visual_total、sound 加總 == audio_total），不符會被 cross_check 擋下。

### 6 大類自檢（不可整類遺漏，漏列等於沒思考過）

對下列每一類明確判斷此 feature 是否需要。需要就列子類與數量，不需要才省略該 key：

- **image**：所有靜態圖片（背景、按鈕、icon、卡片、橫幅、狀態圖、彈窗素材） — 幾乎所有 UI feature 都需要
- **animation**：動畫（領取、慶祝、彈窗開啟、狀態切換等 Lottie/AE）
- **sound**：音效（按鈕點擊、領獎、倒數、警示） — 有互動就需要
- **video**：影片（教學、過場、宣傳） — 多數不需要
- **font**：特殊字型（主視覺數字、品牌字）
- **particle**：粒子特效（金幣、光點、煙火）

思考順序：先想 UI 有哪些畫面 → 每個畫面有哪些圖、動畫、音效 → 彙整成子類計數。
**禁止只給 animation/font/particle 卻漏 image/sound**（reviewer 會擋）。

### Format — 必為 nested dict 子類拆分（reviewer R12 強制）

每個 asset 大類（image / animation / sound / video / font / particle）
必須是 `{子類名: int}` 的 nested dict，**不准只給整數總數**。

**錯誤範例**：
```json
"dryrun": { "resource_counts": { "image": 24, "sound": 6 } }   ❌  reviewer 退
```

**正確範例**：
```json
"dryrun": {
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
    },
    "visual_total": 29,
    "audio_total": 6
  },
  "test_counts": {
    "acceptance_criteria": 12
  },
  "tech_counts": { "api_endpoints": 8, "db_tables": 5, "redis_keys": 1 }
}
```

子類名要具描述性。下游 assets.assets[].category 必須對應某個子類 key。

Write real integers — no `<N>` placeholders.

## DRYRUN — 三組必填估算（timeline 輸入 + 下游最低約束）

`dryrun` 有三個子物件，全部必填：

| 子物件 | 用途 |
|---|---|
| `tech_counts` | 技術規模估算，供 timeline 公式和 spec-advanced cross_check 使用 |
| `resource_counts` | 美術資源 SSOT，供 art timeline 公式和 assets cross_check 使用 |
| `test_counts` | 驗收計數 SSOT，供 planner timeline 公式和 bdd cross_check 使用 |

### dryrun.tech_counts（三個必填整數）

```json
"dryrun": {
  "tech_counts": {
    "api_endpoints": 8,
    "db_tables": 5,
    "redis_keys": 1
  }
}
```

### 如何估算 `api_endpoints`

分兩個面向逐一計數，合計：

**玩家面（player wireframes）**：每張玩家線稿上每個需要向伺服器取值或送資料的操作算 1 個 API（頁面初始化 load、按鈕觸發動作、查詢、領獎 …）。

**後台面（admin wireframes）**：每個被管理員管理的實體（活動、獎勵、玩家記錄、報表 …）需要 CRUD，估法：`實體數 × 3～5`（list + get + create/update + delete + export）。後台面 API 通常不比玩家面少。

**永遠額外加**：
- 認證相關（login / token-refresh / logout）：固定 +3
- 若有非同步回調（金流 payout callback / 第三方通知）：每個 webhook +1

### 如何估算 `db_tables`

從需求（rules / user_journey / business_logic 欄位）推導，逐類檢查：

| 類別 | 說明 | 有無需求 |
|---|---|---|
| `users` / `sessions` | 永遠需要 | 必加 |
| 主實體表 | 每個核心概念（活動、任務、獎品 …）一張 | 依需求 |
| `transactions` / `ledger` | 有任何虛擬幣/點數/金流操作 → 必須獨立 audit table | 幾乎必加 |
| `user_progress` / `participation` | 玩家個人進度、打卡、任務完成狀態 | 依需求 |
| `commissions` / `agent_splits` | 提到代理商、分潤、多層返水 → 必加 | 依需求 |
| `config` / `feature_flags` | 後台可調整的活動參數 | 依需求 |
| `audit_log` | iGaming 法規幾乎必要，操作記錄不可覆蓋 | **iGaming 預設必加** |

**iGaming 最低底限：任何功能至少 5 張 table**（users + 主實體 + transactions + user_progress + audit_log）。若你算出的數字 < 5，重新檢查有無漏算。

### 如何估算 `redis_keys`

- 無排行榜、無 rate-limiting、無 session cache → 填 0
- 有排行榜（leaderboard）：+1
- 有速率限制（每日上限、防刷）：+1
- 有 session / token cache：+1
- 有熱點資料 cache（活動設定、公告）：+1

### tech_counts 的雙重用途

1. **Timeline 計算**：`server_engineer_days = dryrun.tech_counts.api_endpoints × 1.0`（見下方公式）
2. **下游最低約束**：spec-advanced 實際產出的 `apis` 數必須 ≥ `api_endpoints`、`data_models` 中 mysql 數 ≥ `db_tables`、redis 數 ≥ `redis_keys`（程式 cross_check 自動驗，未達標擋住 pipeline）

### dryrun.test_counts（必填）

`acceptance_criteria` = `len(acceptance_criteria[])` — 即你在本文件 `acceptance_criteria` 陣列裡列出的條目總數。

```json
"dryrun": {
  "test_counts": {
    "acceptance_criteria": 12
  }
}
```

用途：`planner_days = dryrun.test_counts.acceptance_criteria × 0.25`（timeline 公式）；bdd cross_check 也用此數字驗 scenario 數量是否足夠。

### dryrun.resource_counts（必填，見上方 RESOURCE COUNTS 節）

`visual_total`/`audio_total` 及各美術大類子類 dict 填法見 RESOURCE COUNTS 節，此處不重複。
用途：`art_days = (visual_total + audio_total) × 8/43`（timeline 公式）；assets cross_check 用此對齊實際產出。

估算要誠實，不要刻意壓低也不要膨脹。spec-advanced 的設計者看到 dryrun 是「輸入估算」，他們仍須從實際設計推導每一個 API，cross_check 只是確認沒有嚴重缺漏。

---

## TIMELINE — 估時公式（純 spec-basic 自洽，不准依下游）

每個 `timeline[]` phase 必填 `duration_weeks` (integer)。

**Per-role budget**（4 主要角色平行做，elapsed = max(per-role) / 5 無條件進位整數週）：

| role | day/item coef | metric 來源（**全在 spec-basic 內部**） |
|---|---|---|
| `art` | 0.2 day | `dryrun.resource_counts.visual_total + audio_total`（dryrun 自報總數）|
| `server_engineer` | 1.0 day | `dryrun.tech_counts.api_endpoints`（**整數，見上方 DRYRUN 節**）|
| `client_engineer` | 0.67 day | `len(wireframes)` |
| `planner` | 0.2 day | `len(user_journey) + len(admin_journey) + len(matrix.rows)` + 固定 5 |

**total_weeks 算法**：

```
total_weeks = ceil(max(art_days, server_days, client_days, planner_days) / 5)
```

無條件進位成整數週（半週半天不能上線）。
`timeline[*].duration_weeks` 加總必須**剛好等於** total_weeks（不可多、不可少）。

範例：8 api → server 8 day；43 asset → art 8.6 day；7 wf → client 4.69 day；5 sect → planner 1 day → max 8 day → ceil(8/5) = **2 週**

**有 AI 協助**，傳統「4 週 + 3 週」估時錯了 — 此公式是按 1 點 = 1 工作天校準。

**為什麼公式只看 spec-basic 自己**：spec-basic 是 step 1，重生時下游（spec-advanced/assets/scrum）不存在或可能 stale。`api_endpoints` 由 AI 在 DRYRUN 節自報，不靠去讀 spec-advanced。下游 step 自己會驗 sa.apis 實際數 vs dryrun.tech_counts.api_endpoints 估算數是否對齊。

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

6. **wf-row 限制 (inline-only)**：wf-row 的直接 children 必須是 inline class
   (`wf-pill` / `wf-tag` / `wf-btn` / `wf-link` / `wf-icon` / `wf-line` /
   `wf-helper` 等)。禁止 `wf-panel` / `wf-card` / `wf-board` / `wf-banner` /
   `wf-table` 等 block primitive 當 wf-row 直接 child — 會撐爆 mobile 寬度。
   - ❌ `<div class="wf-row"><div class="wf-panel">D1</div><div class="wf-panel">D2</div></div>`
   - ✅ 要做格子網格用 `wf-pill` 排成多個 `wf-row`：
     `<div class="wf-stage"><div class="wf-row"><span class="wf-pill">D1</span><span class="wf-pill">D2</span></div><div class="wf-row">…</div></div>`
   - ✅ 要堆 panel 改用 `wf-stage` 直接包多個 `wf-panel` 縱向疊放，不要塞進 wf-row。
   - 例外：`wf-modal` 子樹內 wf-row 可放 wf-panel（modal 自有寬度，
     side-by-side 選擇樣式合法）。
   - 違反 → reviewer `wireframe_row_contains_block` + cross_check 擋。

### Output 格式

## ADMIN JOURNEY — 有後台時必填

`spec-basic.input.json` 必含 `admin_journey: []` — 跟 `user_journey` 結構同
（action / detail / role optional），但描述**管理員**的後台操作流程：

**Admin self-consistency 雙向強制**（cross_check 程式驗）：
- 有任一 wireframe `name` 含「後台」/`admin` → `admin_journey` 必非空（reviewer `admin_journey_missing` 擋）
- `admin_journey` 非空 → 必有對應 admin wireframe（reviewer `admin_wireframe_missing_for_journey` 擋）
- 兩個都沒 → OK（純玩家 feature）
- 沒 admin wireframe → 可省略 `admin_journey`

**下游 prototype 規定**：proto-help「下一步」陣列長度 = `user_journey.length + admin_journey.length`（每步 1:1 對應），AI 不准取捨。這直接決定 prototype 演示有沒有走完整。

範例見 canonical `spec-basic.input.json` `admin_journey`。

## WIREFRAMES

Output a `wireframes` array covering **every distinct UI screen** this
feature touches. **No arbitrary upper cap** — list them all. Sources you
MUST scan:

- **每個 `user_journey` 步驟** → 對應一個玩家畫面（主畫面、彈窗、領獎成功 …）
- **每個 `/admin/`、`/internal/`、`/dashboard/`、`/console/` API 路徑** → 對應一個後台畫面。後台不是「一張籠統管理頁」— 每個獨立功能（設定面板、玩家記錄列表、報表、權限管理 …）算**獨立 wireframe**
- **每個錯誤狀態（401/403/404/空資料）** → 對應一個空狀態 / 錯誤頁
- **每個 modal / 確認框 / 提示彈窗** → 算獨立 screen

範例分類（依 feature 性質實際挑）：
- 玩家：主畫面 / 領獎彈窗 / 排行榜 / 設定頁 / 空狀態 / 斷簽提示
- **後台 (admin)**：活動設定面板 / 玩家記錄列表 / 後台儀表板 / 權限管理

每筆 entry：
```json
{"name":"主畫面","desc":"一句話描述","html":"<div class=\"wf-scope\">…</div>"}
{"name":"後台 — 玩家記錄列表","desc":"管理員依活動查玩家簽到狀態","html":"<div class=\"wf-scope\">…</div>"}
```

**禁止**：把後台壓成一條「後台管理頁」；admin / scrum admin story / `/admin/`
API 沒對應的獨立 wireframe（reviewer 會用 `wireframe_admin_uncovered` 擋）。

### 後台 wireframe — class 硬規定（程式檢查擋）

後台 (name 含「後台」/`admin`) 必須用 **desktop primitives**，**禁用 mobile/loading 元件**：

**容器**：
- ✅ `wf-desktop`（單面後台）或 `wf-desktop-app` + `wf-sidebar`（含左側導覽）
- ❌ `wf-frame`（mobile/通用窄欄，後台**禁用**）

**頂部 / 導覽**：`wf-topbar` + `wf-breadcrumb`

**主內容區**：`wf-main`

**表單**（活動設定、編輯）：
- ✅ `wf-form-grid` > `wf-form-row` > 標籤 `wf-line` + 輸入 `<input class="wf-input">` / `<input class="wf-input-date">` / `<select class="wf-select">` / `<textarea class="wf-textarea">`
- ❌ `<div class="wf-skeleton-pill">` 當輸入框（**禁用** — 那是 shimmer 讀取佔位）

**表格**（玩家記錄、報表）：
- ✅ `wf-toolbar`（搜尋 + 按鈕）→ `<div class="wf-table">` > `<div class="wf-tr">` > `<div class="wf-td">` → `wf-pagination`
- ❌ 一排 `<span class="wf-pill">` 當欄位標題 + 另一排 pills 當資料（**禁用** — pill 是 28px 小徽章不是儲存格）

**KPI / 報表**：`wf-cards-grid` > 多個 `wf-stat-card`

違反任一條 → cross_check 自動發 issue：`admin_wireframe_wrong_container` / `admin_form_uses_skeleton_pill` / `admin_table_uses_pills`，fixer 必修。完整速查見 `templates/wireframe-dsl.md` 第 7 節。

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
