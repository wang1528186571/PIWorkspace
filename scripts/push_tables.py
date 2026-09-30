#!/usr/bin/env python3
"""把论文表格 tables.json 推送到服务器（scp）。

用法（在工作站上）:
    python3 scripts/push_tables.py --file /path/to/tables.json
生成 tables.json 的逻辑后续接入实验工作站的 paper_tables，本脚本只管运输。
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def _load_env_local():
    """本地私有配置 .env.local（不入库）：KEY=VALUE，每行一条。"""
    p = Path(__file__).resolve().parent.parent / ".env.local"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env_local()
SERVER = os.environ.get("WORKBENCH_SERVER", "user@your-server")
DEST = "/opt/workbench/data/tables.json"


def main():
    parser = argparse.ArgumentParser("push_tables")
    parser.add_argument("--file", required=True, help="tables.json 路径")
    parser.add_argument("--server", default=SERVER)
    parser.add_argument("--dest", default=DEST)
    args = parser.parse_args()

    cmd = ["scp", args.file, "%s:%s" % (args.server, args.dest)]
    print("+", " ".join(cmd), flush=True)
    rc = subprocess.call(cmd)
    if rc != 0:
        print("推送失败 (rc=%d)" % rc, file=sys.stderr)
        sys.exit(rc)
    print("已推送 → %s:%s（页面刷新「论文表格」即可见）" % (args.server, args.dest))


if __name__ == "__main__":
    main()
