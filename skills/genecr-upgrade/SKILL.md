---
name: genecr-upgrade
description: |
  手動升級 genecr（git pull + re-deploy + re-build tools）。
  預設**只升當前 host**（看 skill 自己被部署在哪）。
  呼叫時機：user 說「升級 genecr」「genecr 更新」「update genecr」「/genecr-upgrade」。
allowed-tools:
  - Bash
---

# genecr-upgrade — 升級 genecr（同 host）

## 決定 host

看上方系統訊息「Base directory for this skill: …」的路徑：

- 路徑含 `.claude` → host = **claude** → `GENECR_DIR=$HOME/.claude/skills/genecr`
- 路徑含 `.codex`  → host = **codex**  → `GENECR_DIR=$HOME/.codex/skills/genecr`

依此把下面 bash 的 `GENECR_DIR` 替換正確路徑（**不要用 for-loop 自動偵測，會跨 host**）。

## Step

```bash
# 依當前 host 設定（看上方 Base directory 的路徑判斷）
GENECR_DIR="$HOME/.claude/skills/genecr"   # ← 若從 .codex 載入請改 $HOME/.codex/skills/genecr

if [ ! -d "$GENECR_DIR/.git" ]; then
  echo "❌ $GENECR_DIR 不是 git repo，請先 install"
  exit 1
fi
source "$GENECR_DIR/bin/genecr-env.sh"
bash "$GENECR_DIR/setup" upgrade
```

完成後告知使用者：「✅ genecr 已更新（$GENECR_HOST），重開 $GENECR_HOST 讓新 skill 生效。」

> 同時升 claude + codex：`bash "$GENECR_DIR/setup" upgrade all`
