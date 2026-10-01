# 🧪 PIWorkspace

**English | [简体中文](README.zh-CN.md)**

A lightweight research-workspace web app written in **pure Python standard library** —
zero third-party dependencies, one tiny server, single-page UI, accessible from
phone / tablet / desktop browsers.

> ⭐ **The design inspiration and feature architecture come from the open-source project
> [ny12031/research_system](https://github.com/ny12031/research_system)** (a Tauri-based
> research workspace desktop app, MIT License). PIWorkspace is an independent Web
> re-implementation of those ideas — no code was copied. See
> [Credits](#credits) for details.

## Features

- **Today dashboard** — stat chips (todo / done / papers / projects / open questions)
  plus a topic-stats card with **daily / weekly / monthly / yearly** switcher, and a
  conference countdown card (e.g. CVPR D-41)
- **Check-ins** — start / end work multiple times a day, leave records, automatic
  work-hour totals, quick fixes
- **Tasks** — priority, due dates, overdue badges
- **Papers** — register papers; click into one to see its **data tables and figures**
  - grouped table headers; experiment groups (comparison / transfer / visualization…)
    become horizontal tabs, auto-generated from pushed data
  - editable in place: create/rename experiment groups, build manual tables
    (name, groups, headers, values, add/remove rows & columns), rename pushed tables —
    stored in `state.json` (`projects[].workspace`), pushed data stays untouched
- **Research projects** — track engineering projects and status
- **Submissions** — conference calendar with deadline countdowns + custom targets
- **Open questions** — note blockers, check them off when solved
- **Daily retro** — done / blockers / next focus, one entry per day
- **Statistics** — dedicated page with per-day work-hour bars
- **Auto data backup** — every save is committed and pushed to a private GitHub repo

## Quick Start

Python ≥ 3.8, no pip dependencies:

```bash
python3 server/workbench.py --port 8900
# open http://127.0.0.1:8900
```

## Server Deployment (nginx + basic auth)

The app listens on `127.0.0.1` only; nginx provides the public `auth_basic` entry:

```bash
# on the server
rsync the code to /opt/workbench
cp deploy/workbench.service /etc/systemd/system/ && systemctl enable --now workbench
apt install nginx
printf "user:$(openssl passwd -apr1 'your-password')" > /etc/nginx/workbench.htpasswd
cp deploy/nginx-workbench.conf /etc/nginx/conf.d/workbench.conf
nginx -t && systemctl reload nginx
```

Day-to-day updates: `scripts/deploy_server.sh user@your-server` (rsync + service
restart, never touches data).

## Data & Auto Backup

All state lives in a few small files under `--data-dir` (default `./data/`):

| File | Written by | Purpose |
|---|---|---|
| `state.json` | web UI (POST /api/data) | tasks / targets / questions / check-ins / retros / papers / projects, atomic writes |
| `tables.json` | workstation push (read-only) | paper tables; `"topic"` assigns to a paper, `"exp"` is the experiment group |
| `conferences.json` | manual (read-only) | conference calendar, data from [ccfddl](https://github.com/ccfddl/ccf-deadlines) |
| `artifacts.json` + `files/` | `push_artifacts.py` | paper figures, served safely at `/files/<name>` (path-traversal protected) |

Auto backup: wire `scripts/data_backup.sh` to a systemd timer (templates in `deploy/`)
to commit and push `data/*.json` to your own **private** repo; production setups also
trigger it from the save hook in `server/workbench.py` (throttled to 2 minutes).

Pushing tables / figures (from the workstation; the server address lives in
`.env.local`, which is never committed):

```bash
echo "WORKBENCH_SERVER=user@your-server" > .env.local
python3 scripts/push_tables.py --file tables.json
python3 scripts/push_artifacts.py --topic "Paper title" --exp "Visualization" fig1.png
```

`tables.json` contract (`columns[].group` for grouped headers, `topic` / `exp` for
ownership):

```json
{
  "updated": "2026-09-30 21:00",
  "tables": [
    {"id": "cmp", "topic": "Paper title", "exp": "Comparison", "title": "Comparison",
     "columns": [{"key":"method","label":"Method"},
                 {"key":"v5s","label":"YOLOv5s","group":"White-box"}],
     "rows": [{"label":"Ours","cells":{"method":"Ours","v5s":12.3}}]}
  ]
}
```

## Credits

The **feature design, information architecture and UI layout** of this project are
inspired by the following open-source projects:

### [ny12031/research_system](https://github.com/ny12031/research_system)

- **Project**: 科研工作台 — a local all-in-one academic management desktop tool for
  researchers (Tauri 2 + Rust + JavaScript)
- **License**: MIT
- **What was referenced**:
  - information architecture: today dashboard / tasks / submissions / check-ins /
    daily retro / statistics
  - check-in interaction (multiple start/end work segments, leave records, work-hour totals)
  - the "daily / weekly / monthly / yearly" switcher of the topic statistics card
  - grouped left sidebar navigation and card-style layout
- **Differences**: PIWorkspace is an independent Web re-implementation (pure Python
  stdlib + single-page HTML, multi-device browsers). Modules not implemented by choice:
  focus timer, self-care, health tracking, advisor management, achievements. Added on
  top: paper archiving (tables / figures grouped by experiment), conference calendar
  (ccfddl data), automatic data backup to GitHub.

### [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines)

- Source of the conference deadline data (CVPR / ICLR …), aggregated into `conferences.json`

## License

MIT
