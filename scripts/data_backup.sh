#!/usr/bin/env bash
# 数据自动备份：把 /opt/workbench/data/*.json 提交并推送到私有备份仓
# PIWorkspace-data（服务器→GitHub 直连，无需代理）。
# 幂等：无变化时不产生 commit。由 workbench.py 保存后触发（节流）+ systemd timer 兜底。
set -euo pipefail
# 真实配置放 <data>/backup.env（不入库），默认值为占位示例
BACKUP_ENV="${BACKUP_ENV:-/opt/workbench/data/backup.env}"
[ -f "$BACKUP_ENV" ] && . "$BACKUP_ENV"
SRC="${SRC:-/opt/workbench/data}"
WORK="${WORK:-/root/workbench-data}"
BACKUP_REPO="${BACKUP_REPO:-git@github.com:yourname/your-data-repo.git}"
GIT_KEY="${GIT_KEY:-$HOME/.ssh/your_deploy_key}"
export GIT_SSH_COMMAND="ssh -i $GIT_KEY -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes"

mkdir -p "$WORK"
if [ ! -d "$WORK/.git" ]; then
  git init -q "$WORK"
  git -C "$WORK" symbolic-ref HEAD refs/heads/main
  git -C "$WORK" remote add origin "$BACKUP_REPO"
fi
mkdir -p "$WORK/data"
# shellcheck disable=SC2046
cp "$SRC"/*.json "$WORK/data/" 2>/dev/null || true

cd "$WORK"
git add -A
if git diff --cached --quiet; then
  exit 0
fi
git -c user.name="workbench-backup" -c user.email="backup@workbench.local" \
  commit -q -m "data backup $(date '+%Y-%m-%d %H:%M:%S')"
git push -q -u origin main
echo "backed up: $(date '+%F %T')"
