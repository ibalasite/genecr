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

# genecr-flow — 跑完整 pipeline

把使用者的需求描述（brief）一路產出 7 份文件。**Host-neutral**，自動定位 runtime（`~/.claude/skills/genecr` 或 `~/.codex/skills/genecr`）。

---

## Step 1：定位 runtime

```bash
if [ -z "$GENECR_DIR" ]; then
  for d in "$HOME/.codex/skills/genecr" "$HOME/.claude/skills/genecr"; do
    [ -d "$d/.git" ] && export GENECR_DIR="$d" && break
  done
fi

if [ -z "$GENECR_DIR" ] || [ ! -d "$GENECR_DIR/.git" ]; then
  echo "❌ 找不到 genecr runtime。請先安裝："
  echo "  git clone https://github.com/ibalasite/genecr.git ~/.claude/skills/genecr"
  echo "  ~/.claude/skills/genecr/setup claude"
  exit 1
fi

source "$GENECR_DIR/bin/genecr-env.sh"
```

## Step 2：確認 pipeline 工具已安裝

```bash
if [ ! -f "$GENECR_TOOLS/pipeline.py" ]; then
  echo "[setup] 首次執行，跑 renderer setup..."
  bash "$GENECR_DIR/tools/renderer/setup.sh" install
fi
```

## Step 3：呼叫 pipeline.py，傳入使用者 brief

把使用者完整的需求描述當作單一字串參數傳給 `pipeline.py --new`。
使用者的 brief 由 skill 觸發時的訊息提供（移除前綴指令字後保留主體）。

```bash
# $BRIEF 由你（AI）從使用者訊息中萃取出來，然後填入下方
BRIEF="<在這裡放使用者完整的需求描述>"

# 從 cwd 跑（pipeline.json 預設讀 cwd 下的 ./pipeline.json，
# 若 cwd 沒有，就用 runtime 帶的範例 pipeline）
PIPELINE_JSON="./pipeline.json"
[ -f "$PIPELINE_JSON" ] || PIPELINE_JSON="$GENECR_DIR/pipeline.json"

python "$GENECR_TOOLS/pipeline.py" "$PIPELINE_JSON" --new "$BRIEF"
```

## Step 4：回報產出位置

跑完後 `pipeline.py` 會印出 `Run: output/<slug>/<datetime>` 與 7 個 step 的 ✅ 狀態。
告知使用者：

```
✅ genecr-flow 完成！文件已產出至：
   $GENECR_DIR/output/<slug>/<datetime>/

包含：
  📋 spec-basic.md / spec-advanced.md
  🎨 assets.md
  🧪 bdd.md
  📌 scrum.md
  🎮 prototype.html
  🌐 docs.html  ← 在瀏覽器開啟看完整文件中心
```

---

## 用法範例

```
user: /genecr-flow 我想做一個隨時可以買賓果的遊戲, 有機會 2000 倍大獎, RTP 99%

→ skill 萃取 brief = "我想做一個隨時可以買賓果的遊戲, 有機會 2000 倍大獎, RTP 99%"
→ 執行 python $GENECR_TOOLS/pipeline.py --new "<brief>"
→ 7 個 step 跑完，產出在 $GENECR_DIR/output/<slug>/<timestamp>/
```

## 可選旗標（給進階使用者）

直接呼叫 `pipeline.py` 時可加：

- `--status` — 不做事，只看最近一次 run 的進度
- `--watch` — 持續監看（每 2 秒掃一次）
- 不帶 `--new` — 接續最近一次未完成的 run（重用該 run 的 brief.txt）
- 改 `pipeline.json` 的 `ai.stub_mode` 為 `false` 才會真的呼叫 AI；否則只跑模板測試
