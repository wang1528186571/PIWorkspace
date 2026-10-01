#!/usr/bin/env bash
# 本地查看版：把服务器上的真实数据拉到 data2/ 并本地起服务（快照用途，正式编辑请在服务器网址上做）
# 用法：scripts/local_view.sh [--sync]   （--sync 强制重新拉取；首次自动拉取）
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env.local ] && . .env.local
SERVER="${WORKBENCH_SERVER:-user@your-server}"
mkdir -p data2
if [ "${1:-}" = "--sync" ] || [ ! -f data2/state.json ]; then
  scp -q "$SERVER:/opt/workbench/data/*.json" data2/
  echo "已从服务器同步最新数据 → data2/"
fi
echo "本地查看版 → http://127.0.0.1:8905  (Ctrl+C 退出)"
exec python3 server/workbench.py --host 127.0.0.1 --port 8905 --data-dir "$PWD/data2"
