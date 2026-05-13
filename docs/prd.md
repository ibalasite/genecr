<!-- Version: v2.0 -->
# GeneCR — 完整產品需求文件（PRD）

> 版本：v2.0 ｜ 日期：2026-05-14
> 作者：Evans（sayyogames.com）

---

## 一、產品願景

GeneCR 讓 iGaming 公司的企畫人員，能透過一句 brief，產出讓**整個開發團隊都能直接使用**的需求文件套件。

**使用對象**：企畫 / 美術 / 動畫師 / 音效師 / Client 工程師（Cocos）/ Server 工程師（Node.js）/ QA / SCRUM Master。

**核心價值**：
- 一行 brief → 7 份文件，省去 1-2 週重複撰寫成本
- 程式控制流程、jsonschema 驗證、AI 只負責內容，結果穩定可預測
- Host-neutral：Claude Code 與 Codex CLI 通吃

---

## 二、核心架構

### 2.1 流程（program-orchestrated）

```
brief（自然語言）
   ↓
pipeline.py 依 pipeline.json 控制
   ↓
[step 1..7] 對每一 step：
   AI generate → jsonschema validate → fail? → AI fix（最多 3 次）→ pass → renderer
   ↓
output/<slug>/<datetime>/<slug>-<type>.md|.html
```

**關鍵**：流程由程式控制，AI 只做「內容生成」「修錯」兩件事；schema 由程式判斷對錯；檔名 / 路徑由程式產生（AI 不能干擾）。

### 2.2 7 份產出

| # | 檔案 | 內容 |
|---|------|------|
| 1 | `<slug>-spec-basic.md` | 企畫版規格書 — 含 wireframes（wf-* DSL）+ 6+ 競業深度分析（mechanic / RTP / payout / user_flow / differentiation / weakness）|
| 2 | `<slug>-spec-advanced.md` | 技術規格書 — Mermaid 架構圖 + Cocos client 設計 + API 列表 + MySQL schema + Redis cache 策略 |
| 3 | `<slug>-assets.md` | 資源清單 + 完整 AI Prompt（圖像 / 音效）|
| 4 | `<slug>-bdd.md` | BDD（Gherkin 中英文 + 每個 scenario 配 sequenceDiagram + 標註涉及 API + 資料來源）|
| 5 | `<slug>-scrum.md` | SCRUM 故事卡（5 群組：基礎/美術/邏輯/獎勵/QA）|
| 6 | `<slug>-prototype.html` | 互動原型 — AI 自由產 inline HTML/CSS/JS（依 spec-basic 的 wireframes 設計），零依賴、375px mobile-first |
| 7 | `<slug>-docs.html` | 整合 docs — gendoc-style sidebar（📁 文件 / 📑 本頁目錄）+ API explorer（sidebar 點 endpoint 試打 + Copy cURL）|

### 2.3 技術棧（強制套用）

| 層 | 技術 | Driver |
|---|---|---|
| Client | Cocos Creator | — |
| Server | Node.js + Express | — |
| DB | MySQL | mysql2 / Sequelize |
| Cache | Redis | ioredis |

prompts 明確帶這套 stack；spec-advanced / bdd / scrum 一律按此產出。

---

## 三、實作層

### 3.1 Pipeline driver

`tools/renderer/pipeline.py`：
- 讀 `pipeline.json`（步驟定義 + 依賴）
- 為每 step 組合 prompt（內嵌 brief / schema / example / 上一步輸出 / 上次 errors）
- 呼叫 `claude -p` 子程序
- jsonschema 驗證；fail 進 fix loop（最多 N 次，預設 3）
- pass 後呼叫 `render.py` 渲染

### 3.2 OUTPUT 慣例

`OUTPUT_ROOT = Path.cwd() / "output"`：
- 寫到使用者 CWD，不污染 runtime
- 路徑：`<cwd>/output/<feature.slug>/<YYYYMMDD-HHMMSS>/`
- 每次 `--new` 開新時間戳；不帶 `--new` 自動 resume 最新一次未完成 run

### 3.3 Templates

```
templates/
├── *.tmpl                      # Jinja2 模板（7 份）
├── schemas/<type>.schema.json  # JSON Schema（驗證 input.json）
├── examples/<type>.input.json  # canonical example（placeholder，純結構參考）
└── prompts/
    ├── <type>.prompt.md        # 7 份 generate prompt
    ├── _fix.prompt.md          # 通用 fix prompt（吃 errors + previous_json）
    └── wireframe-dsl.md        # wf-* CSS class 規範（給 spec-basic 內嵌）
```

### 3.4 Skills

| Skill | 觸發 | 動作 |
|---|---|---|
| `/genecr "<brief>"` | 主流程 | AI 萃取 slug+name → 跑 pipeline.py |
| `/genecr-upgrade` | 同 host 升級 | 自動偵測當前 host（看 skill base dir）→ git pull + redeploy |

兩個 skill 都依「Base directory for this skill」header 決定 host，**不用 for-loop 跨 host 偵測**。

---

## 四、品質規範

### 4.1 docs.html

- gendoc-style：頂導覽（深色 slate）+ 左 sidebar（白底）+ 右 main（白底，full viewport）
- Sidebar 兩 tab：📁 文件 / 📑 本頁目錄；可收合（Ctrl+\\）
- 切到 API panel 時，📑 本頁目錄自動列 endpoints；點 endpoint 載入該支試打表單
- API 試打：path/query params 自動偵測（`{xxx}` → input）+ Request Body preset + Try It（前端 mock）+ Copy cURL（inline 顯示）
- Mermaid 圖：點圖開 lightbox，支援滾輪 zoom / 拖曳 pan / +/-/0/ESC 鍵
- 表格：自然寬，超寬時內捲不撐爆頁面
- 互動原型：因 file:// 安全策略，按鈕在新分頁開啟（不 iframe）

### 4.2 prototype.html

- 完全自由設計（AI 從 spec-basic.wireframes + user_journey 建構）
- 零外部依賴（無 CDN、無 link、無遠端 img）
- Mobile-first 375px viewport，深色背景 + iGaming 視覺
- 至少 3 個互動 step（含浮動操作說明面板）

### 4.3 spec-basic 線框圖

- 每份 spec-basic 必須含 `wireframes` 陣列（3-6 張）
- HTML 用 `wf-*` DSL class（`<div class="wf-scope">…</div>`），無彩色、無漸層、無陰影 > 18px
- 主要：`.wf-mobile` / `.wf-modal` / `.wf-frame` / `.wf-stage` / `.wf-pill` / `.wf-btn` / `.wf-skeleton-*`

### 4.4 競業分析

- 至少 6 競業，跨市場（亞洲/北美/LATAM/東南亞）
- 每個競業填 6 欄：`mechanic` / `rtp` / `payout` / `user_flow` / `differentiation` / `weakness`
- URL 必填且渲染為可點連結

### 4.5 BDD

- 每個核心 scenario 至少 3 種：正常 / 邊界 / 異常
- 每個 scenario 附 Mermaid sequenceDiagram（用 MySQL / Redis）
- 涉及 API 用 `[api-xxx]` 連結到技術版錨點

---

## 五、資料邊界（鐵律）

| 動作 | 位置 | 規範 |
|---|---|---|
| 讀 templates / tools / schemas | `$GENECR_DIR`（runtime） | ✅ 唯一來源 |
| 寫產出 | `$CWD/output/<slug>/<datetime>/` | ✅ 唯一可寫 |
| 寫 runtime | runtime 任何位置 | ❌ 絕不 |
| 讀 dev tree（C:/Projects/genecr） | — | ❌ skill 不依賴 |

---

## 六、Change Log

| 版本 | 日期 | 變更摘要 |
|---|---|---|
| v2.0 | 2026-05-14 | **架構重寫**：pipeline.json + tools/renderer 為核心。新增 generate→validate→fix loop、brief 萃取 feature.json、wireframes（wf-* DSL）、6+ 競業深度欄位、gendoc-style docs.html（sidebar tabs + API explorer）、setup 對齊 gendoc 慣例（_deploy_tools / upgrade re-exec / _find_python）。Tech stack 從 Fastify+MongoDB → Express+MySQL。新增 `/genecr` skill。 |
| v1.1 | 2026-05-13 | lucky-wheel 範例下記錄 8 個 P0/P1 issue（線框、寬度、雙語、原型連結、資源完整性、BDD 全展、prototype 響應、競業連結）|
| v1.0 | 2026-05-12 | 初版，定義 7 份產出、Cocos + Node.js + Fastify + MongoDB tech stack |

---

## 七、未來規劃

- [ ] 雙語產出（中＋英 + es / pt-BR / ja）
- [ ] PDF 自動產生
- [ ] 自動截取競業平台截圖（Playwright）
- [ ] 與 JIRA / Linear 整合（自動建立 Story）
- [ ] 節慶主題模式（聖誕、農曆新年）
- [ ] 多 LLM 適配（OpenAI / Gemini，目前綁 Claude CLI）

---

*文件版本：v2.0 ｜ 由 GeneCR 專案維護*
