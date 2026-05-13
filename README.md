# genecr — iGaming 功能需求文件自動生成器

> **G**ame D**e**sign **C**reation + **R**equirements
> 讓一份需求文件，同時服務企畫、工程、美術、QA。

把一個 iGaming 功能需求，自動轉成讓**整個開發團隊都能直接使用**的完整文件套件：
企畫基礎版、進階技術版、資源清單＋AI Prompt、BDD 測試案例、SCRUM 故事卡、
切換式 HTML 文件、可互動 HTML 原型。

**Host-neutral**：同時支援 [Claude Code](https://claude.com/claude-code) 與 [Codex CLI](https://github.com/openai/codex)，skill 內容不綁死任何一家。

---

## 目錄結構

```
genecr/
├── README.md
├── SKILL.md                       # 主 skill — 章節骨架 / i18n 詞表已內聯，無外部檔依賴
├── setup                          # bash (Git Bash / macOS / Linux)，支援 claude|codex|all
├── setup.ps1                      # PowerShell (Windows)
├── bin/
│   ├── genecr-env.sh              # host-neutral：從自身位置反推 $GENECR_DIR
│   └── genecr-env.ps1
├── skills/
│   └── genecr-upgrade/            # 子 skill — 部署時 copy 到 host 的 skills/
├── templates/                     # 所有必要 asset 一次帶齊（完全離線）
│   ├── wireframe-dsl.md           # 低保真線框圖 DSL 規範（必讀）
│   ├── wireframe-snippets.html    # DSL 對應的 CSS + HTML 範例（複製貼上即用）
│   ├── genecr-template.html       # 切換式 HTML 文件 master template（system font，無 CDN）
│   └── mermaid.min.js             # mermaid v11 離線版（2.5 MB，禁止 CDN 規則所需）
├── tools/bin/
├── assets/
├── evals/
├── references/                    # 本機保留（公司範本等），預設 gitignore
└── output/                        # 使用者執行 genecr 後產生的文件（gitignore）
```

**部署行為**：
1. `git clone <REPO_URL> <host-skills-dir>/genecr`（每個 host 各 clone 一份）
2. 跑 `setup [claude|codex|all]` 把 `genecr/skills/*/` 部署到該 host 的 `skills/`
3. 主 skill `genecr` 從 runtime root 的 `SKILL.md` 直接生效（host 掃 `skills/*/SKILL.md`）

**資料來源邊界（鐵律）**：
- Skill 執行時，**只**從 runtime（由 `$GENECR_DIR` 定位）讀 templates / tools
- **絕不**從開發者的工作樹（如 `C:/projects/genecr/`）讀任何檔案
- 產出物**只**寫到使用者當前工作目錄下的 `./output/[feature-slug]/`
- 所有 skill 開頭必須 `source "$GENECR_DIR/bin/genecr-env.sh"`（**不可**寫死 `~/.claude/...`）

**離線保證**：
- ❌ 不抓 Google Fonts / cdn.jsdelivr / unpkg / cdnjs（templates 已淨化）
- ❌ 不依賴 `references/` 內任何檔（章節結構 + i18n 詞表已內聯進 SKILL.md）
- ✅ 唯一需要網路的是**競業調查**階段的 WebSearch / WebFetch（可選，斷網會跳過）

---

## 安裝

### 🟣 Claude Code

#### macOS / Linux / Windows (Git Bash)

```bash
git clone https://github.com/ibalasite/genecr.git ~/.claude/skills/genecr
~/.claude/skills/genecr/setup claude
```

#### Windows (PowerShell)

```powershell
git clone https://github.com/ibalasite/genecr.git "$env:USERPROFILE\.claude\skills\genecr"
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1" claude
```

### 🟢 Codex CLI

#### macOS / Linux / Windows (Git Bash)

```bash
git clone https://github.com/ibalasite/genecr.git ~/.codex/skills/genecr
~/.codex/skills/genecr/setup codex
```

#### Windows (PowerShell)

```powershell
git clone https://github.com/ibalasite/genecr.git "$env:USERPROFILE\.codex\skills\genecr"
& "$env:USERPROFILE\.codex\skills\genecr\setup.ps1" codex
```

### 🔁 兩個都要

```bash
# 任一已 clone 的 runtime 都可以執行 all（會把兩邊都裝起來）
~/.claude/skills/genecr/setup install all
# 或 PowerShell
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1" install all
```

安裝完成後**重啟 Claude Code / Codex** 讓新 skill 生效。
往後對話說「升級 genecr」即會自動執行 `setup upgrade`（git pull + redeploy 當前 host）。

---

## 使用

安裝後，在 Claude Code 或 Codex 任意對話中描述 iGaming 功能需求即可觸發，例如：

> 我要建立 iGaming 排行榜機制，週排行榜，玩家下注金額累積積分，前 10 名可以領獎

genecr 會自動：
1. 深度競業調查（北美 / 哥斯大黎加 / 東南亞 / 台灣）
2. 產出 7 份文件到當前工作目錄 `./output/[feature-slug]/`：
   - `*-spec-basic.md`（企畫版規格書 + wireframe）
   - `*-spec-advanced.md`（技術版）
   - `*-assets.md`（資源清單 + AI Prompt）
   - `*-bdd.md`（BDD + sequenceDiagram）
   - `*-scrum.md`（SCRUM 故事卡）
   - `*-docs.html`（切換式 HTML 文件，含 API 試打面板，**離線** mermaid）
   - `*-prototype.html`（互動原型）

詳細產出規格請見 [`SKILL.md`](./SKILL.md)。

### Codex 注意事項（sandbox / approval）

Codex 對檔案與命令更重視 sandbox。genecr 執行期間會：

| 動作 | 範圍 | 是否需要 approval |
|------|------|-----------------|
| 讀取 `$GENECR_*` 內所有檔案 | runtime（已安裝目錄） | ❌ |
| 寫入 `./output/<slug>/` | user CWD | 視 Codex 設定 |
| `git pull`（升級 skill 時） | runtime | ✅（網路） |
| WebSearch / WebFetch 競業調查 | 外網 | ✅（網路） |
| 寫入 `~/.claude/...` 或 `~/.codex/...` | home | ✅（升級 / 安裝時） |

如果 Codex 在 sandbox 模式下，建議：競業調查可改用本地 references；升級指令在 host 外手動執行。

---

## 升級

```bash
# 任一 host 的 runtime 都可以執行 upgrade
~/.claude/skills/genecr/setup upgrade           # 只升 claude
~/.codex/skills/genecr/setup upgrade            # 只升 codex
~/.claude/skills/genecr/setup upgrade all       # 兩邊都升

# 對話內：說「升級 genecr」會自動跑（會自動偵測當前 host）
```

---

## 開發

`~/.claude/skills/genecr/` 或 `~/.codex/skills/genecr/` 本身就是 git working tree，直接在那裡編輯：

```bash
cd ~/.claude/skills/genecr   # 或 ~/.codex/skills/genecr
# ...edit...
./setup upgrade              # 把 skills/* 重新部署到當前 host
# 滿意後 git commit && git push
```

別的機器跑 `setup upgrade` 即會 git pull 同步。

---

## 解除安裝

```bash
~/.claude/skills/genecr/setup uninstall          # 移除 claude
~/.codex/skills/genecr/setup uninstall           # 移除 codex
~/.claude/skills/genecr/setup uninstall all      # 兩邊都移除
```
