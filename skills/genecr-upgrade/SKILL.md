---
name: genecr-upgrade
description: |
  手動升級 genecr skills（git pull + re-deploy）。
  呼叫時機：user 說「升級 genecr」「genecr 更新」「update genecr」「/genecr-upgrade」。
allowed-tools:
  - Bash
---

# genecr-upgrade — 手動升級 genecr

從 GitHub 拉最新版並重新部署 subskills。Host-neutral：自動偵測 genecr 安裝在 `~/.claude/skills/genecr` 還是 `~/.codex/skills/genecr`。

---

## Step 1：定位 runtime 並執行升級

```bash
# 1. 找到 GENECR_DIR — 不綁定特定 host
if [ -z "$GENECR_DIR" ]; then
  for d in "$HOME/.codex/skills/genecr" "$HOME/.claude/skills/genecr"; do
    [ -d "$d/.git" ] && export GENECR_DIR="$d" && break
  done
fi

if [ -z "$GENECR_DIR" ] || [ ! -d "$GENECR_DIR/.git" ]; then
  echo "❌ 找不到 genecr runtime（已查 ~/.codex/skills/genecr 和 ~/.claude/skills/genecr）"
  echo "請先安裝："
  echo "  Claude: git clone https://github.com/ibalasite/genecr.git ~/.claude/skills/genecr && ~/.claude/skills/genecr/setup claude"
  echo "  Codex:  git clone https://github.com/ibalasite/genecr.git ~/.codex/skills/genecr  && ~/.codex/skills/genecr/setup codex"
  exit 1
fi

source "$GENECR_DIR/bin/genecr-env.sh"

# 2. 跑 setup upgrade — 自動偵測 host
bash "$GENECR_DIR/setup" upgrade
```

升級完成後告知使用者：「✅ genecr 已更新至最新版（$GENECR_HOST），重開 $GENECR_HOST 讓新 skill 生效。」

> 若要升級所有 host：執行 `bash "$GENECR_DIR/setup" upgrade all`
