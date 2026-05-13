---
name: genecr-upgrade
description: |
  手動升級 genecr skills（git pull + re-deploy）。
  呼叫時機：user 說「升級 genecr」「genecr 更新」「update genecr」「/genecr-upgrade」。
allowed-tools:
  - Bash
---

# genecr-upgrade — 手動升級 genecr

從 GitHub 拉最新版並重新部署 subskills。

---

## Step 1：執行升級

```bash
source "$HOME/.claude/skills/genecr/bin/genecr-env.sh"

if [[ ! -d "$GENECR_DIR/.git" ]]; then
  echo "❌ 找不到 genecr runtime（$GENECR_DIR）"
  echo "請先安裝：git clone <REPO_URL> ~/.claude/skills/genecr && ~/.claude/skills/genecr/setup"
  exit 1
fi

bash "$GENECR_DIR/setup" upgrade
```

升級完成後告知使用者：「✅ genecr 已更新至最新版，重開 Claude Code 讓新 skill 生效。」
