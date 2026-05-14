# genecr — iGaming 功能需求文件自動生成器

> **G**ame D**e**sign **C**reation + **R**equirements
> 一句 brief，產出讓**整個團隊都能直接用**的 7 份文件套件。

把一個 iGaming 功能需求，自動轉成完整文件套件：
企畫版（含線框圖）、技術版（API + Mermaid）、資源清單＋AI Prompt、BDD、SCRUM、互動原型、整合 docs.html。

**Host-neutral**：同時支援 [Claude Code](https://claude.com/claude-code) 與 [Codex CLI](https://github.com/openai/codex)。

---

## 📦 範例輸出

- **刮刮券**（scratch-card）—
  [docs.html](docs/pages/scratch-card/scratch-card-docs.html) ·
  [企畫版](docs/pages/scratch-card/scratch-card-spec-basic.md) ·
  [技術版](docs/pages/scratch-card/scratch-card-spec-advanced.md) ·
  [資源](docs/pages/scratch-card/scratch-card-assets.md) ·
  [BDD](docs/pages/scratch-card/scratch-card-bdd.md) ·
  [SCRUM](docs/pages/scratch-card/scratch-card-scrum.md) ·
  [原型](docs/pages/scratch-card/scratch-card-prototype.html)
- **跨年活動**（new-year-event）—
  [docs.html](docs/pages/new-year-event/new-year-event-docs.html) ·
  [企畫版](docs/pages/new-year-event/new-year-event-spec-basic.md) ·
  [技術版](docs/pages/new-year-event/new-year-event-spec-advanced.md) ·
  [資源](docs/pages/new-year-event/new-year-event-assets.md) ·
  [BDD](docs/pages/new-year-event/new-year-event-bdd.md) ·
  [SCRUM](docs/pages/new-year-event/new-year-event-scrum.md) ·
  [原型](docs/pages/new-year-event/new-year-event-prototype.html)

---

## 架構

```
genecr/
├── README.md
├── pipeline.json              # 流程定義（7 step + AI 設定 + 依賴）
├── setup / setup.ps1          # host 安裝（claude | codex | all）— 仿 gendoc 慣例
├── bin/genecr-env.{sh,ps1}    # runtime 路徑探測（GENECR_DIR/TEMPLATES/...）
├── skills/                    # 部署到 host 的 sub skills
│   ├── genecr/           # /genecr "<brief>" — 跑完整 pipeline
│   └── genecr-upgrade/        # /genecr-upgrade — git pull + redeploy
├── templates/                 # 一切由 pipeline 讀取（離線）
│   ├── *.tmpl                 # 7 份 Jinja2 模板（spec-basic / spec-advanced / assets / bdd / scrum / prototype / docs）
│   ├── schemas/               # JSON Schema — 用於 generate→validate→fix loop
│   ├── examples/              # canonical 範例 input.json（純 placeholder，不綁特定 feature）
│   ├── prompts/               # 7 份 AI prompt（含 _fix.prompt.md fix-loop 通用版）
│   └── wireframe-dsl.md       # 低保真線框圖 DSL（wf-* class 規範）
└── tools/
    ├── renderer/              # 源碼
    │   ├── pipeline.py        # 流程驅動：brief → generate → validate → fix → render
    │   ├── render.py          # 單 type 渲染（template + JSON → 輸出檔）
    │   ├── orchestrate.py     # 一次跑 7 step（manifest 模式）
    │   ├── build.sh           # 由 setup _deploy_tools 自動呼叫，cp .py → ../bin/
    │   └── requirements.txt   # jinja2 / jsonschema / markdown
    └── bin/                   # 由 build.sh 同步，**正式執行入口**
        └── (render.py, pipeline.py, orchestrate.py — 自動產生)

# 使用者執行後產出（在 user 的 CWD，不污染 runtime）
output/<feature-slug>/<YYYYMMDD-HHMMSS>/
├── brief.txt                  # 使用者需求描述
├── feature.json               # {slug, name}（從 brief 萃取）
├── *.combined.prompt.md       # AI 看到的最終 prompt（含 brief / schema / example 內嵌）
├── *.input.json               # AI 產出的結構化資料
├── <slug>-spec-basic.md       # 企畫版（含 wireframes、6+ 競業深度分析）
├── <slug>-spec-advanced.md    # 技術版（API、Mermaid、MySQL schema）
├── <slug>-assets.md           # 資源清單 + AI Prompt
├── <slug>-bdd.md              # BDD（Gherkin + sequence diagram）
├── <slug>-scrum.md            # SCRUM 故事卡
├── <slug>-prototype.html      # 互動原型（zero-dep, mobile-first）
└── <slug>-docs.html           # 整合 docs（sidebar + tab + API explorer）
```

**鐵律**：
- runtime（`$GENECR_DIR`）只讀；不寫任何使用者資料進 runtime
- 所有產出寫到 user CWD 下的 `./output/<slug>/<datetime>/`
- skill 開頭一律 `source "$GENECR_DIR/bin/genecr-env.sh"`

**離線**：
- ❌ 不抓 CDN（mermaid.min.js 內附；docs.html 用內聯 mermaid）
- ✅ 唯一需要網路：跑時 AI 自己選擇是否用 web research（可斷網跳過）

---

## 安裝

### 🟣 Claude Code

```bash
git clone https://github.com/ibalasite/genecr.git ~/.claude/skills/genecr
~/.claude/skills/genecr/setup claude
```

### 🟢 Codex CLI

```bash
git clone https://github.com/ibalasite/genecr.git ~/.codex/skills/genecr
~/.codex/skills/genecr/setup codex
```

### 🔁 兩個都裝

```bash
~/.claude/skills/genecr/setup install all
```

### Windows PowerShell

```powershell
git clone https://github.com/ibalasite/genecr.git "$env:USERPROFILE\.claude\skills\genecr"
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1" claude
```

`setup` 內部依序：`git clone` → `_deploy_skills`（部署 sub skills）→ `_deploy_tools`（跑 `tools/renderer/build.sh` 把 .py 拷到 `tools/bin/`）。

安裝完**重啟** Claude Code / Codex 讓 skill 生效。

---

## 使用

### 一行觸發

在 Claude Code / Codex 任意對話：

```
/genecr 老玩家每儲值 1000 送刮刮券，玩遊戲也會掉，20-5000 倍大獎，未中獎有幸運代號每週抽，不能讓代理商損失
```

或自然語言「**genecr 跑流程做 X 功能**」。

### 流程內部（程式控制，不靠 AI 協調）

```
1. AI 從 brief 萃取 SLUG + NAME → feature.json
2. pipeline.py 依 pipeline.json 順序跑 7 step：
   spec-basic → spec-advanced → assets → bdd → scrum → prototype → docs
   （prototype 依賴 spec-basic；docs 最後合併）
3. 每個 step：
   a. AI generate（讀 brief + schema + example，全部內嵌進 prompt）
   b. jsonschema 驗證（程式判斷，AI 不參與）
   c. 過 → renderer 用 Jinja2 template 渲染成 .md / .html
   d. 不過 → AI fix（讀 errors + 上次 JSON），最多 3 次
4. docs.html 最後集成所有 .md + API explorer（sidebar tab：📁 文件 / 📑 本頁目錄）
```

### 直接呼叫 pipeline.py（進階）

```bash
# 在自己專案目錄下，輸出寫到 ./output/
python ~/.claude/skills/genecr/tools/bin/pipeline.py \
  ~/.claude/skills/genecr/pipeline.json \
  --new --slug bingo --name "賓果" "我想做一個隨時可以買賓果的遊戲..."

# 旗標
--status     # 看最近一次 run 的進度（純看檔案存在性）
--watch      # 持續監看，每 2s 一次
--new        # 強制新時間戳（否則 resume 最新一次未完成 run）
```

---

## 使用手冊

### 1. 如何寫好 brief

Brief 是整個 pipeline 的源頭。寫越具體、結果越貼近期待。

**好 brief 含的要素**：

| 要素 | 範例 |
|---|---|
| 核心機制 | 「儲值 1000 送刮刮券」「每天簽到 7 天送神秘禮」 |
| 數字參數 | 「最高 5000 倍」「RTP 99%」「連續 7 天」「每週開獎」 |
| 商業限制 | 「不能讓代理商損失」「不影響既有平衡」「預算每月 X 萬」 |
| 目標族群 | 「老玩家」「VIP 月卡用戶」「新會員」 |
| 觸發時機 | 「隨時可買」「每日上線」「進入大廳就觸發」 |

**好 brief 範例**：

> 老玩家每儲值 1000 送刮刮券，玩遊戲也會掉，最高 5000 倍，未中獎有幸運代號每週抽，不能讓代理商損失

7 個關鍵字一次到位：對象（老玩家）+ 觸發（儲值 / 遊戲掉）+ 倍率（5000 倍）+ 安慰機制（幸運代號）+ 週期（每週開獎）+ 商業限制（不傷代商）。

**差 brief 範例**：

> 做一個刮刮樂

AI 只能猜。產出會很泛、缺商業細節。

**訣竅**：把腦中所有「不能 / 必須 / 至少 / 最多」都寫進去，AI 會把這些寫進業務規則、防作弊、邊界 case。

---

### 2. 7 份文件導覽

| 檔案 | 給誰看 | 用法 |
|---|---|---|
| `<slug>-spec-basic.md` | 企畫 / PM / 美術 | 主規格書 + wireframes — 給上游確認方向；美術依 wireframes 開資源 |
| `<slug>-spec-advanced.md` | Server / Client 工程師 | 含完整 API 列表 + Mermaid 架構 + MySQL schema + Redis key 設計 — 直接給後端排 sprint |
| `<slug>-assets.md` | 美術 / 音效師 | 每個資源含 AI prompt（英文）— 可直接貼 Midjourney / Suno 出圖出音 |
| `<slug>-bdd.md` | QA / Tech Lead | Gherkin 中英文 + 每 scenario 含 sequenceDiagram — 可直接 import 進測試框架 |
| `<slug>-scrum.md` | SCRUM Master / PM | 故事卡分 5 群（基礎/美術/邏輯/獎勵/QA）+ 點數 + 負責團隊 — 直接貼 JIRA |
| `<slug>-prototype.html` | UX / 老闆 demo | 互動原型，瀏覽器打開就玩。Mobile-first，可丟手機看 |
| `<slug>-docs.html` | **所有人** | 整合 docs 入口 — sidebar 切換、API 試打面板、Mermaid lightbox |

**檢視順序建議**：
1. 先看 `docs.html` → 把所有東西串在一起
2. 上游：`spec-basic.md` + `prototype.html`
3. 下游：`spec-advanced.md` + `bdd.md` + `assets.md` + `scrum.md`

---

### 3. 常見指令對照

| 我想… | 指令 |
|---|---|
| 跑一份新文件 | `/genecr "<brief>"` |
| 看上一次跑到哪 | `python tools/bin/pipeline.py --status` |
| 接續中斷的 run | `python tools/bin/pipeline.py`（不帶 `--new` 自動 resume） |
| 同 feature 開新時間戳重跑 | `python tools/bin/pipeline.py --new --slug X --name Y "<brief>"` |
| 跟著看 step 即時進度 | `python tools/bin/pipeline.py --watch` |
| 只看某個 type 的渲染結果 | `python tools/bin/render.py <type> <input.json> <out>` |

---

### 4. 修改與重跑

每次 run 都是一個獨立目錄 `output/<slug>/<YYYYMMDD-HHMMSS>/`。可以：

**(a) 改 brief 重跑**

```bash
# 開新時間戳，舊 run 保留作對照
python tools/bin/pipeline.py --new --slug bingo --name "賓果" "新版 brief"
```

**(b) 改某個 step 的 input.json 後重 render**

例如想自己微調 spec-basic 的競業列表：

```bash
RUN=output/bingo/20260514-101530
vim "$RUN/spec-basic.input.json"           # 改完
python tools/bin/render.py spec-basic "$RUN/spec-basic.input.json" "$RUN/bingo-spec-basic.md"
# 下游 docs.html 也重 render：
python tools/bin/render.py docs "$RUN/docs.input.json" "$RUN/bingo-docs.html"
```

pipeline 純檔案驅動：刪一個 `.md` 再執行 `pipeline.py`（不帶 `--new`）會只重做缺的那步。

**(c) 看 AI 看到了什麼 prompt**

每個 step 留下 `<step>.combined.prompt.md` — 完整的 generate prompt（已內嵌 brief / schema / example）。除錯時可直接看。

---

### 5. 故障排除

| 症狀 | 可能原因 | 怎麼處理 |
|---|---|---|
| `step.errors.1.txt` 內容是 `JSON parse error: Expecting value at line 1 column 1` | AI 回應是 0 bytes 或非 JSON | 看 `<step>.combined.prompt.md` 確認 prompt 有沒怪；通常重跑就好 |
| schema fail，errors 列出缺哪些 required 欄位 | AI 漏填欄位 | 自動 fix loop 會跑 2 次（attempt 2, 3）通常會修好 |
| 3 次都過不了 | prompt 太鬆或 schema 太嚴 | 看 `errors.<n>.txt`；考慮修 prompt 或暫時放鬆 schema |
| 全 0 bytes、AI 沒回應 | `claude -p` 沙箱權限問題（檔案外路徑） | 我們已內嵌 brief/schema/example 不靠 Read tool；若還 0 bytes 檢查 claude CLI 是否能跑 |
| `claude: command not found` | Claude CLI 沒裝 / 不在 PATH | `npm i -g @anthropic-ai/claude-code` 或改 `pipeline.json` 的 `ai.command` 指向你的 CLI |
| docs.html 開不出 prototype 內容 | iframe 被 `file://` 安全策略擋 | 新版已改為「在新分頁開啟」按鈕（不 iframe）|
| Mermaid 圖點放大空白 | 之前 clone-and-rerender bug | 新版已修（用 `data-source` 保原始碼）|
| docs sidebar TOC 沒項目 | 當前 panel 沒 h1-h4 標題 | API panel 自動列 endpoints；其他 panel 需有 markdown 標題 |

**Debug 流程**：
```bash
RUN=output/<slug>/<datetime>

# 1. 看 pipeline.py 完整 log（背景跑時看 stdout 截圖）
# 2. 看每個 step 的 combined prompt（AI 看到什麼）
cat "$RUN/<step>.combined.prompt.md"

# 3. 看每次 fix 嘗試的錯誤
cat "$RUN/<step>.errors.1.txt"
cat "$RUN/<step>.errors.2.txt"

# 4. 看 AI 真實產出
cat "$RUN/<step>.input.json"
```

---

### 6. Codex CLI 使用情境

Codex 的 sandbox 模型比 Claude Code 嚴，需要特別注意：

**安裝**：

```bash
git clone https://github.com/ibalasite/genecr.git ~/.codex/skills/genecr
~/.codex/skills/genecr/setup codex
```

**使用**：

```
# 在 Codex CLI 對話中
/genecr 老玩家每儲值 1000 送刮刮券…
```

**Sandbox 注意事項**：

| 動作 | 影響 | 對策 |
|---|---|---|
| 讀 `$GENECR_DIR/*`（runtime） | 已是 `~/.codex/...` 內，安全範圍 | ✅ 不需處理 |
| 寫 `./output/<slug>/<datetime>/` | 寫到當前 CWD | 確認 Codex 對 CWD 有寫權限；通常你的工作目錄 OK |
| `claude -p` 呼叫 | Codex 內**沒有** `claude` CLI | 改 `pipeline.json` 的 `ai.command` 為 Codex 自己的 CLI（例如 `codex exec`），或在 host 機器另裝 Claude CLI |
| `git pull`（升級時）| 網路 + runtime 寫入 | 需要 approval；對話中明確說「升級 genecr」 |

**Codex 改 ai.command 範例**（實測指令）：

```jsonc
// ~/.codex/skills/genecr/pipeline.json
{
  "ai": {
    // 預設給 Claude CLI 用：
    // "command": "claude -p --output-format text < {prompt} > {output}",
    //
    // Codex 版（stdin 餵 prompt，-o 寫最終訊息到檔案）：
    "command": "codex exec --skip-git-repo-check -o {output} < {prompt}",
    "stub_mode": false
  },
  ...
}
```

> 為何不用 stdout redirect？`codex exec` stdout 含 "tokens used" 統計行；`-o <file>` 只寫最終 agent message，剛好是我們要的 JSON。

**Sandbox 升級**：預設 Codex 對 file write 嚴格，可能擋到 `output/` 目錄。需要時加：

```bash
codex exec -s workspace-write --skip-git-repo-check -o {output} < {prompt}
```

或暫時：`codex exec --dangerously-bypass-approvals-and-sandbox ...`（**不建議常用**）。

**多 host 切換**：兩邊都裝後，`/genecr` skill 自動識別當前 host（看 skill base directory 路徑含 `.claude` / `.codex`），不會跨 host 干擾。

**競業調查**：若 Codex 在純離線 sandbox，AI 無法做 web research，會 fallback 用內建知識。產出仍可用但較少現役競品 URL。

**驗證 Codex 環境 OK**：

```bash
echo "Reply with just the word OK" | codex exec --skip-git-repo-check -o /tmp/codex-test.txt
cat /tmp/codex-test.txt    # 應該看到「OK」
```

通過代表 Codex CLI 可被 pipeline 呼叫。

---

## 技術棧（產出文件套用）

| 層 | 技術 |
|---|---|
| Client | Cocos Creator |
| Server | Node.js + Express |
| DB | MySQL |
| Cache | Redis |

prompts 對 AI 明確指定，產出的 spec-advanced / bdd / scrum 都以此為準。

---

## 升級

```bash
~/.claude/skills/genecr/setup upgrade           # 只升 claude
~/.codex/skills/genecr/setup upgrade            # 只升 codex
~/.claude/skills/genecr/setup upgrade all       # 兩邊都升

# 或對話內：「升級 genecr」會觸發 /genecr-upgrade（同 host 自動偵測）
```

升級流程：`git pull` → `exec setup _post_upgrade <host>`（gendoc-style re-exec，新版 setup 立即生效）→ `_deploy_skills` + `_deploy_tools`（rebuild tools/bin/）。

---

## 開發

`~/.claude/skills/genecr/` 本身就是 git working tree。但**建議**：

```bash
git clone https://github.com/ibalasite/genecr.git ~/dev/genecr
cd ~/dev/genecr
# ...edit...

# 直接跑 source（不必先 build）：
python tools/renderer/pipeline.py pipeline.json --new --slug X --name Y "brief"

# 同步 source → bin（部署檢查）：
BIN_DIR="$(pwd)/tools/bin" PACKAGE_DIR="$(pwd)/tools/renderer" PY="python" \
  bash tools/renderer/build.sh

git push
# 別處跑 /genecr-upgrade 即拉到最新
```

**不要直接編輯 runtime（`~/.claude/skills/genecr/`）**：每次 `/genecr-upgrade` 會被覆蓋。

---

## 解除安裝

```bash
~/.claude/skills/genecr/setup uninstall          # 只移除 claude
~/.codex/skills/genecr/setup uninstall           # 只移除 codex
~/.claude/skills/genecr/setup uninstall all      # 兩邊都移除
```
