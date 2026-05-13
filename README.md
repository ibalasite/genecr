# genecr — iGaming 功能需求文件自動生成器

> **G**ame D**e**sign **C**reation + **R**equirements
> 一句 brief，產出讓**整個團隊都能直接用**的 7 份文件套件。

把一個 iGaming 功能需求，自動轉成完整文件套件：
企畫版（含線框圖）、技術版（API + Mermaid）、資源清單＋AI Prompt、BDD、SCRUM、互動原型、整合 docs.html。

**Host-neutral**：同時支援 [Claude Code](https://claude.com/claude-code) 與 [Codex CLI](https://github.com/openai/codex)。

---

## 架構

```
genecr/
├── README.md
├── pipeline.json              # 流程定義（7 step + AI 設定 + 依賴）
├── setup / setup.ps1          # host 安裝（claude | codex | all）— 仿 gendoc 慣例
├── bin/genecr-env.{sh,ps1}    # runtime 路徑探測（GENECR_DIR/TEMPLATES/...）
├── skills/                    # 部署到 host 的 sub skills
│   ├── genecr-flow/           # /genecr-flow "<brief>" — 跑完整 pipeline
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
/genecr-flow 老玩家每儲值 1000 送刮刮券，玩遊戲也會掉，20-5000 倍大獎，未中獎有幸運代號每週抽，不能讓代理商損失
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
