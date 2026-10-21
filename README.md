# quicklink · 短链工坊

一句话定位：一个轻量、可自托管的短链接服务——把长网址变短、302 跳转、带点击统计，单用户自用。

设计学习了开源社区短链接工具的通行思路（短码、点击计数与点击日志），代码为独立实现（溯源见 UPSTREAM.md）。

## 功能清单

- 单用户登录（Token 24 小时有效，首次登录提示改密）
- 生成短链：贴长网址即生成 6 位随机短码；也可自定义后缀（被占用会明确报错）
- 跳转：访问 `/{短码}` 以 302 跳到原网址；短链可停用（停用后返回 410 提示页）或删除
- 点击统计：每次跳转记一条（时间、来源 Referer、设备大类），每条短链显示总点击与最近 20 条记录
- 管理：按长网址/短码搜索，按创建时间或点击量排序
- 单页前端：生成、复制、统计、停用/启用、删除都在一个页面完成

## 快速开始

默认账号：`admin` / `admin123`（首次登录会提示改密；可用环境变量
`QL_INITIAL_USERNAME` / `QL_INITIAL_PASSWORD` 覆盖初始账号密码）。

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Windows（PowerShell）

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

启动后打开 http://127.0.0.1:8000 ，用默认账号登录即可。
端口可用环境变量 `QL_PORT` 修改；数据库默认在 `data/quicklink.db`，
可用 `QL_DB_PATH` 指定其他位置。

## 测试

先装开发依赖，再跑自动化测试与真实流程自测：

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python tests/live_selftest.py
```

（Windows 同样是这两条命令，在已激活 venv 的 PowerShell 里执行。）

`live_selftest.py` 会真的起一个服务进程，走一遍"登录 → 生成短链 → 跳转 →
查点击统计 → 停用 → 再跳转应为 410"的完整流程并逐项打勾。

## 项目结构

- `app.py` — 后端（FastAPI + SQLite）：账号、短链、跳转、统计接口
- `static/index.html` — 单页前端（原生 HTML/JS，无构建步骤）
- `tests/test_app.py` — 自动化测试
- `tests/live_selftest.py` — 真实服务自测脚本
- `NOTES.md` — 设计调研笔记
- `UPSTREAM.md` — 上游溯源信息

## 说明

- 点击日志只记录设备大类（桌面浏览器 / 移动端 / 机器人等），不存 UA 原文、不存访客 IP。
- 本项目为个人自托管用途的单用户版本，不含多用户、插件、二维码等功能。
