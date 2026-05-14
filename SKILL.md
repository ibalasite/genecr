---
name: genecr
description: |
  跑 genecr 完整 pipeline：使用者描述功能需求，自動產出 7 份文件
  （企畫版/技術版/資源/BDD/SCRUM/原型/docs.html）。
  呼叫時機：user 說「genecr 跑流程」「跑 genecr pipeline」「生成完整文件」
  「我想做一個 X 遊戲」「/genecr 我想做 …」。
allowed-tools:
  - Bash
---

# genecr — 跑完整 pipeline（同 host）

## 1. 決定 host

看上方「Base directory for this skill」：
- 含 `.claude` → `GENECR_DIR=$HOME/.claude/skills/genecr`，預設用 `pipeline.json`
- 含 `.codex`  → `GENECR_DIR=$HOME/.codex/skills/genecr`，改用 `pipeline-codex.json`（若存在；否則編輯 `pipeline.json` 的 `ai.command`）
- 含 `.gemini` → `GENECR_DIR=$HOME/.gemini/skills/genecr`，改用 `pipeline-gemini.json`

## 2. 從 brief 萃取 feature 資訊（你的職責，AI）

讀使用者完整需求描述（brief），萃取兩個值：

- **`SLUG`** — 英文、小寫、kebab-case、≤ 20 字元，能反映核心功能
  - 範例：「我想做一個賓果遊戲」→ `bingo`
  - 範例：「排行榜功能」→ `leaderboard`
  - 範例：「每日簽到任務」→ `daily-checkin`
- **`NAME`** — 該功能的中文名稱（短，2-6 字）
  - 範例：「我想做一個賓果遊戲」→ `賓果`
  - 範例：「排行榜功能」→ `排行榜`

## 3. 執行 pipeline

```bash
GENECR_DIR="$HOME/.claude/skills/genecr"   # ← 若從 .codex / .gemini 載入請改

source "$GENECR_DIR/bin/genecr-env.sh"

# 依 host 選 pipeline.json：gemini → pipeline-gemini.json；其他 → pipeline.json
case "$GENECR_HOST" in
  gemini) PIPELINE_FILE="pipeline-gemini.json" ;;
  *)      PIPELINE_FILE="pipeline.json" ;;
esac
PIPELINE_JSON="./$PIPELINE_FILE"
[ -f "$PIPELINE_JSON" ] || PIPELINE_JSON="$GENECR_DIR/$PIPELINE_FILE"

# 由你（AI）依步驟 2 萃取後填入
SLUG="bingo"          # ← 從 brief 萃取的英文 slug
NAME="賓果"            # ← 從 brief 萃取的中文 name
BRIEF="<使用者完整需求描述>"

python "$GENECR_TOOLS/pipeline.py" "$PIPELINE_JSON" \
  --new --slug "$SLUG" --name "$NAME" "$BRIEF"
```

## 4. 完成後回報

`pipeline.py` 會印 `Run: output/<slug>/<datetime>` + 7 step 狀態。告訴使用者：

```
✅ genecr 完成！產出在：
   $GENECR_DIR/output/<slug>/<datetime>/

  📋 spec-basic.md / spec-advanced.md
  🎨 assets.md
  🧪 bdd.md
  📌 scrum.md
  🎮 prototype.html
  🌐 docs.html  ← 在瀏覽器開啟看完整文件中心
```

## 旗標（直接用 pipeline.py 時）

- `--status` 只看狀態，不做事
- `--watch` 持續監看
- 不帶 `--new` → 接續最近一次未完成的 run（自動找最新 run，不需 `--slug`）
- 重新跑同 slug：`--new --slug <已存在的 slug>` → 開新時間戳資料夾
