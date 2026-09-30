#!/usr/bin/env python3
"""把课题图片推送到服务器并登记进 artifacts.json（多端可见）。

用法（在工作站上）:
    python3 scripts/push_artifacts.py --topic "DrivePatch 对抗纹理" fig1.png fig2.png
    可选: --title "消融ASR曲线" --note "口径说明"

图片落到服务器 data/files/，manifest 追加到 data/artifacts.json；
网页「科研工作 → 点开课题 → 图片」即显示。文件名冲突时自动加时间戳后缀。
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
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
DEST_DIR = "/opt/workbench/data/files"
MANIFEST = "/opt/workbench/data/artifacts.json"


def sh(cmd, input_bytes=None):
    r = subprocess.run(cmd, capture_output=True, input=input_bytes)
    return r.returncode, r.stdout, r.stderr


def main():
    parser = argparse.ArgumentParser("push_artifacts")
    parser.add_argument("--topic", required=True, help="归属课题名（须与网页登记的课题名一致）")
    parser.add_argument("--exp", default="", help="实验分组名（如 对比实验/迁移实验/可视化效果，详情页横排标签）")
    parser.add_argument("--title", default="", help="图片标题（默认用文件名）")
    parser.add_argument("--note", default="", help="备注")
    parser.add_argument("files", nargs="+", help="本地图片路径 png/jpg/svg/webp/pdf")
    parser.add_argument("--server", default=SERVER)
    args = parser.parse_args()

    # 1. 取当前 manifest（不存在则空表）
    rc, out, err = sh(["ssh", args.server, "cat %s 2>/dev/null" % MANIFEST])
    try:
        manifest = json.loads(out.decode("utf-8")) if rc == 0 and out.strip() else {}
    except Exception:
        manifest = {}
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), list) else []

    # 2. 上传文件（重名加时间戳）
    stamp = datetime.datetime.now().strftime("%H%M%S")
    uploaded = []
    for f in args.files:
        p = Path(f)
        if not p.exists():
            print("跳过（不存在）: %s" % f, file=sys.stderr)
            continue
        remote_name = p.name
        if any(a.get("file") == remote_name for a in artifacts):
            remote_name = "%s_%s%s" % (p.stem, stamp, p.suffix)
        rc, _, err = sh(["scp", str(p), "%s:%s/%s" % (args.server, DEST_DIR, remote_name)])
        if rc != 0:
            print("上传失败 %s: %s" % (f, err.decode()[:200]), file=sys.stderr)
            sys.exit(rc)
        uploaded.append((p, remote_name))
        print("+ %s → %s" % (p.name, remote_name))

    # 3. 追加 manifest 并回传
    for p, remote_name in uploaded:
        artifacts.append({
            "id": "a%d%s" % (int(datetime.datetime.now().timestamp()), remote_name.replace(".", "")),
            "topic": args.topic,
            "exp": args.exp,
            "title": args.title if len(uploaded) == 1 else (p.stem if not args.title else args.title + " " + p.stem),
            "note": args.note,
            "file": remote_name,
        })
    manifest["artifacts"] = artifacts
    manifest.setdefault("updated", datetime.date.today().isoformat())
    manifest["updated"] = datetime.date.today().isoformat()
    payload = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
    rc, _, err = sh(["ssh", args.server, "cat > %s" % MANIFEST], input_bytes=payload)
    if rc != 0:
        print("manifest 写入失败: %s" % err.decode()[:200], file=sys.stderr)
        sys.exit(rc)
    print("已推送 %d 张图 → 课题「%s」（网页科研工作里点开该课题即可见）" % (len(uploaded), args.topic))


if __name__ == "__main__":
    main()
