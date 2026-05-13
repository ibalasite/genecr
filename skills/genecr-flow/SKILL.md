---
name: genecr-flow
description: |
  跑 genecr 完整 pipeline：使用者描述功能需求，自動產出 7 份文件
  （企畫版/技術版/資源/BDD/SCRUM/原型/docs.html）。
  呼叫時機：user 說「genecr 跑流程」「跑 genecr pipeline」「生成完整文件」
  「我想做一個 X 遊戲」「/genecr-flow 我想做 …」。
  用法：直接把使用者的功能描述當作 brief 傳入。
allowed-tools:
  - Bash
---

# genecr-flow — 跑完整 pipeline（同 host）

## 決定 host

看上方「Base directory for this skill」：
- 含 `.claude` → `GENECR_DIR=$HOME/.claude/skills/genecr`
- 含 `.codex`  → `GENECR_DIR=$HOME/.codex/skills/genecr`

## Step：執行 pipeline

```bash
# 依當前 host 設定（看上方 Base directory）
GENECR_DIR="$HOME/.claude/skills/genecr"   # ← 若從 .codex 載入請改

source "$GENECR_DIR/bin/genecr-env.sh"

# pipeline.json：cwd 優先，不在就用 runtime 帶的範例
PIPELINE_JSON="./pipeline.json"
[ -f "$PIPELINE_JSON" ] || PIPELINE_JSON="$GENECR_DIR/pipeline.json"

# AI：把使用者完整需求描述當作 BRIEF（移除指令字後保留主體）
BRIEF="<在這裡放使用者完整的需求描述>"

python "$GENECR_TOOLS/pipeline.py" "$PIPELINE_JSON" --new "$BRIEF"
```

## 完成後

`pipeline.py` 會印出 `Run: output/<slug>/<datetime>` 與 7 step 狀態。告知使用者：

```
✅ genecr-flow 完成！產出在：
   $GENECR_DIR/output/<slug>/<datetime>/

  📋 spec-basic.md / spec-advanced.md
  🎨 assets.md
  🧪 bdd.md
  📌 scrum.md
  🎮 prototype.html
  🌐 docs.html  ← 在瀏覽器開啟看完整文件中心
```

## 旗標（直接用 pipeline.py 時）

- `--status` 只看狀態
- `--watch` 持續監看
- 不帶 `--new` → 接續最近一次未完成的 run
