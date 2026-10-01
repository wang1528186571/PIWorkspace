#!/usr/bin/env bash
# 日常部署：rsync 代码到服务器并重启服务（不碰 data/，不影响 nginx）
set -euo pipefail
# 服务器地址：环境变量 WORKBENCH_SERVER 或 .env.local 或命令行第一参数
[ -f "$(dirname "$0")/.env.local" ] && . "$(dirname "$0")/.env.local"
SERVER="${WORKBENCH_SERVER:-${1:-user@your-server}}"
DEST=/opt/workbench
cd "$(dirname "$0")/.."
rsync -a --delete \
  --exclude .git --exclude data --exclude data2 --exclude __pycache__ --exclude '*.pyc' \
  ./ "$SERVER:$DEST/"
ssh "$SERVER" "systemctl restart workbench && sleep 1 && systemctl is-active workbench"
echo "deployed → http://$SERVER:28488  (服务端口 127.0.0.1:8900)"
