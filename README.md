# genecr — iGaming 功能需求文件自動生成器

> **G**ame D**e**sign **C**reation + **R**equirements
> 讓一份需求文件，同時服務企畫、工程、美術、QA。

把一個 iGaming 功能需求，自動轉成讓**整個開發團隊都能直接使用**的完整文件套件：
企畫基礎版、進階技術版、資源清單＋AI Prompt、BDD 測試案例、SCRUM 故事卡、
切換式 HTML 文件、可互動 HTML 原型。

---

## 目錄結構（仿 gendoc）

```
genecr/
├── README.md
├── SKILL.md         # 主 skill 定義（runtime root 即 genecr skill 本身）
├── setup            # bash 安裝腳本 (Windows Git Bash / macOS / Linux)
├── setup.ps1        # PowerShell 安裝腳本 (Windows 原生)
├── bin/
│   ├── genecr-env.sh    # 路徑單一來源（source 後取得 GENECR_DIR 等）
│   └── genecr-env.ps1   # PowerShell 版
├── skills/
│   └── genecr-upgrade/  # 子 skill — 部署時 copy 到 ~/.claude/skills/genecr-upgrade/
├── templates/       # 共用範本（如 genecr-template.html、lightbox 片段）
├── tools/
│   └── bin/         # 工具腳本（預留）
├── assets/          # skill 靜態資源
├── evals/           # evals.json
├── references/      # 參考文件
└── output/          # 使用者執行 genecr 後產生的文件成果（**不部署**，git ignore）
```

**部署行為**（與 gendoc 同模式）：
1. `git clone <REPO_URL> ~/.claude/skills/genecr`（runtime 即 git working tree）
2. 跑 `setup` 把 `~/.claude/skills/genecr/skills/*/` 每個子目錄部署到 `~/.claude/skills/`
3. 主 skill `genecr` 從 runtime root 的 `SKILL.md` 直接生效（Claude Code 會掃描 `~/.claude/skills/*/SKILL.md`）

**資料來源邊界（鐵律）**：
- Skill 執行時，**只**從 runtime（`~/.claude/skills/genecr/`，由 `$GENECR_*` 環境變數定位）讀 templates / tools / references
- **絕不**從開發者的工作樹（如 `C:/projects/genecr/`）讀任何檔案
- 產出物**只**寫到使用者當前工作目錄下的 `./output/[feature-slug]/`
- 所有 skill 開頭必須 `source "$HOME/.claude/skills/genecr/bin/genecr-env.sh"`

---

## 安裝

首次安裝先 clone repo 到 `~/.claude/skills/genecr`：

```bash
git clone https://github.com/ibalasite/genecr.git ~/.claude/skills/genecr
```

然後執行 setup：

### macOS / Linux / Windows (Git Bash)

```bash
~/.claude/skills/genecr/setup            # install（預設）
~/.claude/skills/genecr/setup upgrade    # git pull + 重新部署
~/.claude/skills/genecr/setup uninstall  # 移除
```

### Windows (PowerShell)

```powershell
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1"            # install
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1" upgrade
& "$env:USERPROFILE\.claude\skills\genecr\setup.ps1" uninstall
```

安裝完成後**重啟 Claude Code**讓新 skill 生效。
往後在對話說「升級 genecr」即會自動執行 `setup upgrade`（git pull + redeploy）。

---

## 使用

安裝後，在 Claude Code 任意對話中描述 iGaming 功能需求即可觸發，例如：

> 我要建立 iGaming 排行榜機制，週排行榜，玩家下注金額累積積分，前 10 名可以領獎

genecr 會自動：
1. 深度競業調查（北美 / 哥斯大黎加 / 東南亞 / 台灣）
2. 產出 7 份文件到當前工作目錄 `./output/[feature-slug]/`

詳細產出規格請見 [`skills/genecr/SKILL.md`](./skills/genecr/SKILL.md)。

---

## 開發

`~/.claude/skills/genecr/` 本身就是 git working tree，直接在那裡編輯 `SKILL.md` / `templates/` / `skills/`：

```bash
cd ~/.claude/skills/genecr
# ...edit...
./setup upgrade   # 把 skills/* 重新部署到 ~/.claude/skills/
# 滿意後 git commit && git push
```

別的機器跑 `setup upgrade` 即會 git pull 同步。
