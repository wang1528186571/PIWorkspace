#!/usr/bin/env python3
"""科研工作台 Research Workbench — 纯标准库轻量服务端 (Python 3.8+).

模块：每日任务 / 投稿目标 / 当前问题 / 打卡记录 / 论文表格 / 会议日历。
前三者+打卡在网页上直接编辑，整体存 data/state.json；
论文表格(conferences)为只读，由推送/放置 data/tables.json、data/conferences.json 提供。

    python3 server/workbench.py --port 8900
    python3 server/workbench.py --host 127.0.0.1 --port 8900 --data-dir ./data
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
CST = timezone(timedelta(hours=8))
MODULES = ("tasks", "targets", "problems", "checkins", "retros", "projects", "rprojects")
MAX_BODY = 2 * 1024 * 1024  # 2MB，个人工作台足够
LOCK = threading.Lock()
BACKUP_SH = "/opt/workbench/scripts/data_backup.sh"
BACKUP_MIN_INTERVAL = 120  # 秒；保存后触发备份的节流间隔，兜底靠 systemd timer
_last_backup = [0.0]
_backup_lock = threading.Lock()


def maybe_backup():
    """保存后异步备份数据到 GitHub（节流；脚本不存在或本地开发时静默跳过）。"""
    now = time.time()
    with _backup_lock:
        if now - _last_backup[0] < BACKUP_MIN_INTERVAL:
            return
        _last_backup[0] = now

    def run():
        try:
            if os.path.exists(BACKUP_SH):
                subprocess.Popen(
                    ["bash", BACKUP_SH],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
IMG_TYPES = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _load_json_or(path, empty):
    """读取小 JSON；缺失/损坏一律降级为 empty 的浅拷贝，绝不让页面白屏。"""
    if not path.exists():
        return dict(empty)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(empty)
    if not isinstance(data, dict):
        return dict(empty)
    for k, v in empty.items():
        data.setdefault(k, v)
    return data


class Store:
    """data/ 目录下的小 JSON：state.json（可编辑）、tables.json / conferences.json /
    artifacts.json（只读推送），以及 files/ 里的图片等附件。"""

    def __init__(self, data_dir: Path):
        self.dir = data_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.files_dir = data_dir / "files"
        self.files_dir.mkdir(exist_ok=True)
        self.state_path = self.dir / "state.json"
        self.tables_path = self.dir / "tables.json"

    def _empty(self):
        return {m: [] for m in MODULES}

    def load_state(self):
        with LOCK:
            if not self.state_path.exists():
                return self._empty()
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                return self._empty()
            if not isinstance(data, dict):
                return self._empty()
            return {m: (data.get(m) if isinstance(data.get(m), list) else []) for m in MODULES}

    def save_state(self, data):
        clean = {}
        for m in MODULES:
            items = data.get(m)
            clean[m] = items if isinstance(items, list) else []
        payload = json.dumps(clean, ensure_ascii=False, indent=1)
        with LOCK:
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, self.state_path)
        return clean

    def load_tables(self):
        if not self.tables_path.exists():
            return {"updated": None, "tables": []}
        try:
            data = json.loads(self.tables_path.read_text(encoding="utf-8"))
        except Exception:
            return {"updated": None, "tables": []}
        if not isinstance(data, dict):
            return {"updated": None, "tables": []}
        data.setdefault("updated", None)
        data.setdefault("tables", [])
        return data

    def load_conferences(self):
        path = self.dir / "conferences.json"
        empty = {"updated": None, "source": "", "conferences": []}
        return _load_json_or(path, empty)

    def load_artifacts(self):
        path = self.dir / "artifacts.json"
        empty = {"updated": None, "artifacts": []}
        return _load_json_or(path, empty)


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "Workbench/0.1"

        def log_message(self, fmt, *args):
            print("%s %s" % (datetime.now(CST).strftime("%m-%d %H:%M:%S"), fmt % args), flush=True)

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self._send(code, body, "application/json; charset=utf-8")

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                page = APP_ROOT / "web" / "index.html"
                if page.exists():
                    body = page.read_bytes()
                    self._send(200, body, "text/html; charset=utf-8")
                else:
                    self._send(404, "web/index.html missing".encode(), "text/plain; charset=utf-8")
            elif path == "/api/data":
                self._json(store.load_state())
            elif path == "/api/tables":
                self._json(store.load_tables())
            elif path == "/api/conferences":
                self._json(store.load_conferences())
            elif path == "/api/artifacts":
                self._json(store.load_artifacts())
            elif path.startswith("/files/"):
                self._serve_file(path[len("/files/"):])
            else:
                self._json({"error": "not found"}, 404)

        def _serve_file(self, raw_name):
            import urllib.parse
            name = os.path.basename(urllib.parse.unquote(raw_name))
            f = (store.files_dir / name).resolve()
            ext = f.suffix.lower()
            if not f.exists() or f.parent != store.files_dir.resolve() or ext not in IMG_TYPES:
                self._json({"error": "not found"}, 404)
                return
            try:
                body = f.read_bytes()
            except Exception:
                self._json({"error": "read failed"}, 404)
                return
            self._send(200, body, IMG_TYPES[ext])

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path != "/api/data":
                self._json({"error": "not found"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0 or length > MAX_BODY:
                self._json({"error": "bad length"}, 400)
                return
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                self._json({"error": "bad json"}, 400)
                return
            if not isinstance(data, dict):
                self._json({"error": "bad payload"}, 400)
                return
            saved = store.save_state(data)
            maybe_backup()
            self._json({"ok": True, "saved_at": datetime.now(CST).strftime("%H:%M:%S"), "state": saved})

    return Handler


def main():
    parser = argparse.ArgumentParser("research-workbench")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8900)
    parser.add_argument("--data-dir", default=str(APP_ROOT / "data"))
    args = parser.parse_args()

    store = Store(Path(args.data_dir))
    httpd = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(
        "科研工作台 → http://%s:%d  (data: %s, Ctrl+C 退出)"
        % (args.host, args.port, store.dir),
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
