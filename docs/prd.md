<!-- Version: v2.1 -->
# GeneCR — 完整產品需求文件（PRD）

> 版本：v2.1 ｜ 日期：2026-05-20
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

### 2.1.1 review_loop（program-orchestrated 三段獨立 subagent）

v2.1 起每個 step 跑 **generator / reviewer / fixer 三段獨立 subagent**：

```
generator → 程式檢查（jsonschema + cross_check）→ reviewer → fixer → 重來
（finding=0 才收斂；無 hard cap）
```

避免「同一 AI 自我審查」偏差。reviewer 只做語義審查、fixer 只負責修；schema / cross_check 由程式做不交給 AI。

### 2.1.2 cross_check（跨步驟一致性）

`tools/renderer/cross_check.py` 在每個 step 跑完後，由程式驗證跨步驟一致性：

| 規則 | 程式檢查 |
|---|---|
| timeline weeks | == `ceil(max(per-role 公式工作天) / 5)` |
| scrum per-role 加總點數 | ≥ 公式地板（**地板邏輯**：1 點=1 工作天，scrum 拆 Fibonacci 自然 ≥ 地板）|
| 單 story 點數 | ≤ 5（INVEST 原則）|
| assets type 件數 | == sb.resource_counts.{visual,audio}_total |
| spec-advanced SQL WHERE 欄位 | 有對應 index |
| spec-advanced Redis 鍵 | 都先在 data_models 宣告 |

**單一基準 anchor**（從 checkin7v2 baseline 固化）：所有新企畫按量體比例縮放。Anchor 數字（5/8 API + 3/4 MySQL + 2/4 Redis + 8/43 asset + 8/7 wf + 3/12 AC）寫死在 code 中，改要單獨討論。


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
| Step 隔離 | 各 step preprocess 只准讀本 step + upstream（depends_on）| ❌ 不准讀下游 sibling |

## 五-1、GUI distribution（v0.3.x series）

針對「非開發者」user，提供 Windows GUI installer（`gui/` + `installer/`）：

| 組件 | 角色 |
|---|---|
| **安裝工具包**（embed Python，`{app}\python-embed\`）| 安裝期跑 pip / playwright / 協調系統 Python 安裝；user 完全不需碰 Python |
| **主程式 Python**（PATH 上系統 python.exe）| pipeline / renderer 跑時用；找不到 → 自動 winget / .exe 靜默裝 |
| **bootloader splash**（PyInstaller `--splash`）| ~30ms 內顯示，無黑屏等待 |
| **single-instance lock**（socket bind 127.0.0.1:62731）| user 多點不會開多隻 |
| **多 host 自動更新**（`upgrade_all_installed_hosts`）| 啟動時掃 gemini/claude/codex 三套 skill 並 `git pull` + redeploy |
| **🐛 一鍵 bug 回報**（GUI 內按鈕）| 自動帶 env + log + 智慧萃取 `ErrorType: message` 當 GitHub issue title |

build pipeline：`python installer/build.py` 一鍵 = 下載 embed zip + patch _pth + get-pip + PyInstaller `--onedir` + ISCC.exe。


---

## 六、Change Log

| 版本 | 日期 | 變更摘要 |
|---|---|---|
| **v2.1** | **2026-05-20** | **review_loop 三段獨立 subagent**（generator/reviewer/fixer，commit 05b5557 / d6ee31a）；**cross_check 跨步驟一致性**（302a5ac → 970f9d8 → 9abd2c2 → 836fc5a），最終定為**單一基準 anchor + 地板邏輯**（無 hard cap）；**revalidate-by-step**（dd5b15d）既有 output 對新規則重檢；**Step isolation 鐵律**（9abd2c2，step preprocess 禁讀下游 sibling）；**spec-basic 自洽合約**（visual_total / audio_total 必填，sb 不准讀 sa/assets）；**prompts 強化**（5f99fac STAKES + Final human gate、276bc1c PRE-FLIGHT + zh-TW、c9705d9 strict reviewer/fixer skeletons）；spec-advanced 加 stateDiagram + CREATE TABLE DDL + db_queries 渲染（94723c9 + 85e946e ER diagram）；assets 加 owner_role / output_format / suggested_filename / nested resource_counts（353f263 + 6ff40f5 6 production types + Excel pivot index）；**mermaid 完全離線**（23da401 內嵌 mermaid.min.js 取代 CDN、81b6374 sequenceDiagram `;` 自動 escape #59;）；**Windows GUI installer** 完整 release 系列（gui/ + installer/，含 embed Python bundle / 多 host 自動更新 / single-instance lock / bootloader splash / 一鍵 bug 回報 / 雙保險 taskkill 舊版） |
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
