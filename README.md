# 🧪 PIWorkspace（科研工作台）

纯 Python 标准库的轻量科研管理单页应用，零第三方依赖，一台小服务器即可部署，
手机 / 平板 / 电脑浏览器多端访问。

> ⭐ **本项目的设计灵感与功能架构来自开源项目 [ny12031/research_system](https://github.com/ny12031/research_system)**（Tauri 桌面版科研工作台，MIT License）。PIWorkspace 是其设计思路的独立 Web 重写实现，未复制其代码。详细参考范围见文末 [致谢与参考](#致谢与参考credits)。

## 功能特性

- **今日执行舱**：统计小卡（待办 / 已完成 / 学术论文 / 科研项目 / 待解决问题）+ 最近会议倒计时大卡
- **主题统计**：每日 / 每周 / 每月 / 每年 一键切换，从打卡与任务自动汇总，无需手动记录
- **打卡记录**：开始工作 / 结束工作 / 请假，自动统计工时、未结束工作段，支持快速修正
- **项目任务**：优先级、截止日倒计时、逾期提醒
- **学术论文**：登记论文（状态 + 说明），点开可看该论文名下的**数据表格与图片**
  - 表格支持分组表头，实验分组（对比 / 迁移 / 可视化…）自动生成横排标签
- **科研项目**：登记工程性项目与进度状态
- **投稿管理**：会议日历（含截止倒计时与开会地点）+ 自定义投稿目标
- **当前问题**：卡点记录，解决一条划掉一条
- **每日复盘**：今日完成 / 卡点经验 / 明日重点，一天一条
- **数据统计**：独立页，含每日工时柱状图
- **数据自动备份**：每次保存自动提交推送到独立私有仓库（见下文）

## 快速开始

要求 Python ≥ 3.8，无任何 pip 依赖：

```bash
python3 server/workbench.py --port 8900
# 浏览器打开 http://127.0.0.1:8900
```

## 部署到服务器（nginx + basic auth）

应用只监听 `127.0.0.1`，公网入口由 nginx 提供 `auth_basic`：

```bash
# 服务器上
rsync 代码到 /opt/workbench
cp deploy/workbench.service /etc/systemd/system/ && systemctl enable --now workbench
apt install nginx
printf "user:$(openssl passwd -apr1 '你的密码')" > /etc/nginx/workbench.htpasswd
cp deploy/nginx-workbench.conf /etc/nginx/conf.d/workbench.conf
nginx -t && systemctl reload nginx
```

日常更新代码：`scripts/deploy_server.sh user@your-server`（rsync + 重启服务，不动数据）。

## 数据与自动备份

所有状态都在 `--data-dir`（默认 `./data/`）下的几个小文件里：

| 文件 | 谁写 | 说明 |
|---|---|---|
| `state.json` | 网页编辑（POST /api/data） | 任务/目标/问题/打卡/复盘/论文/项目，原子写入 |
| `tables.json` | 工作站推送（只读） | 论文表格；`"topic"` 归属论文，`"exp"` 实验分组 |
| `conferences.json` | 手工维护（只读） | 会议日历，来源 [ccfddl](https://github.com/ccfddl/ccf-deadlines) |
| `artifacts.json` + `files/` | `push_artifacts.py` | 课题图片，`/files/<名>` 安全服务（防路径穿越） |

论文详情支持新建实验、实验改名和手动表格（名称、分组、表头、数值、增删行列）。
选择实验标签后可点击“重命名实验”；点击“添加表格”创建表格，已有表格可点击“编辑表格”。
这些编辑保存在 `state.json` 的 `projects[].workspace` 内，随现有状态同步与备份。
工作站推送表格的显示名称和实验分组可以在网页修改，结果数值继续由工作站更新；
显示设置不修改 `tables.json` 或 `artifacts.json`。推送时保持表格 `id` 稳定可保留名称设置。

自动备份：把 `scripts/data_backup.sh` 配上 `systemd timer`（模板在 `deploy/`），
即可将 `data/*.json` 定时提交推送到你自己的**私有**仓库；也可在
`server/workbench.py` 保存钩子中触发（生产部署默认带，节流 2 分钟）。

表格 / 图片推送（在工作站上执行，服务器地址写进 `.env.local`，该文件不入库）：

```bash
echo "WORKBENCH_SERVER=user@your-server" > .env.local
python3 scripts/push_tables.py --file tables.json
python3 scripts/push_artifacts.py --topic "论文题目" --exp "可视化效果" fig1.png
```

`tables.json` 契约（`columns[].group` 分组表头，`topic`/`exp` 归属）：

```json
{
  "updated": "2026-09-30 21:00",
  "tables": [
    {"id": "cmp", "topic": "论文题目", "exp": "对比实验", "title": "对比实验",
     "columns": [{"key":"method","label":"方法"},
                 {"key":"v5s","label":"YOLOv5s","group":"白盒"}],
     "rows": [{"label":"Ours","cells":{"method":"Ours","v5s":12.3}}]}
  ]
}
```

## 致谢与参考（Credits）

本项目的**功能设计、信息架构与界面布局**参考并致敬以下开源项目：

### [ny12031/research_system](https://github.com/ny12031/research_system)

- **项目**：科研工作台（面向科研工作者的本地一体化学术管理桌面工具，Tauri 2 + Rust + JavaScript）
- **协议**：MIT License
- **参考范围**：
  - 整体信息架构：今日执行舱 / 项目任务 / 投稿管理 / 打卡记录 / 每日复盘 / 数据统计
  - 打卡记录交互（多次开始/结束工作、请假记录、工时统计）
  - 主题统计的「每日 / 每周 / 每月 / 本年」切换设计
  - 左侧分组导航 + 卡片式布局的界面风格
- **本项目的差异**：Web 化重写（纯 Python 标准库 + 单页 HTML，多端浏览器访问）；按自身需求
  未实现专注计时器、心灵关怀、健康管理、导师管理、成就系统等模块；新增学术论文归档
  （表格 / 图片按实验分组展示）、会议日历（ccfddl 数据）、数据自动备份到 GitHub 等

### [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines)

- 会议截止日期数据来源（CVPR / ICLR 等），`conferences.json` 由其公开数据整理

## License

MIT
