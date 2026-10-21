# TASK-041-quicklink 执行记录

开工时间：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-041-quicklink`。先审查再修 P0/P1。

## 1. 环境探测

命令（工作目录 `E:\muse-bridge\in\TASK-041-quicklink`）：

```
python --version
```

输出：

```
Python 3.11.9
```

退出码：0。代码使用 `str | None`（app.py:223），需要 3.10+，当前解释器满足。

虚拟环境放到 `E:\muse-bridge\work\TASK-041-quicklink\.venv`，避免把 `.venv` 写进待审仓库。数据库与日志同样放该工作目录。

README Windows 步骤写的是 `py -m venv`。本机执行：

```
py --version
```

输出（退出码 1）：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

`py` 启动器指向不存在的 `E:\python.exe`，属于本机环境问题，不是仓库缺陷。改用已可用的 `python` 3.11.9 建虚拟环境。

## 2. 安装依赖

```
python -m venv E:\muse-bridge\work\TASK-041-quicklink\.venv
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` 第一行是 `-r requirements.txt`，一次装齐运行与测试依赖。退出码 0。关键行：

```
Successfully installed ... fastapi-0.156.4 ... httpx-0.28.1 ... pytest-9.1.1 ... python-multipart-0.0.32 ... starlette-1.9.0 ... uvicorn-0.54.0
```

版本与 requirements.txt / requirements-dev.txt 的钉死版本一致，无依赖冲突。

## 3. 自动化测试

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pytest tests/ -q
```

工作目录：`E:\muse-bridge\in\TASK-041-quicklink`。退出码 0。

```
...................                                                      [100%]
============================== warnings summary ===============================
..\..\work\TASK-041-quicklink\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-041-quicklink\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
19 passed, 1 warning in 2.74s
```

19 项全部通过。警告来自已安装的 Starlette：建议改用 `httpx2`，当前测试仍通过。未改依赖版本。

## 4. 真实流程自测

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe tests\live_selftest.py
```

退出码 0。

```
[PASS] 服务启动 /health 
[PASS] 登录成功 
[PASS] 生成自定义短链 code=selftest
[PASS] 跳转 302 到原网址 
[PASS] 点击统计为 2 
[PASS] 停用短链 
[PASS] 停用后跳转返回 410 
[PASS] 不存在短码返回 404 

共 8 项，通过 8 项
```

该脚本自己把数据库放到系统临时目录（`tempfile.mkdtemp`，tests/live_selftest.py:28），并在结束时 `proc.terminate()`。端口 8931，不是 README 的 8000。下一步另起一次 8000 端口核对首页和 `/health`。

## 5. 按 README 端口起服务并关闭

数据库放到工作目录，避免在仓库里生成 `data/quicklink.db`。脚本：`E:\muse-bridge\work\TASK-041-quicklink\smoke_server.py`。

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\smoke_server.py
```

退出码 0。标准输出：

```
PID 32688 port 8000
GET /health -> 200 {"status":"ok","app":"quicklink"}
GET / -> 200 content-type=text/html; charset=utf-8
HOME_HAS_LOGIN True
HOME_HAS_TITLE True
HOME_SNIP <!DOCTYPE html> <html lang="zh-CN"> ... <title>quicklink · 短链工坊</title> ...
GET /docs -> 404
STOPPED returncode=1
AFTER_STOP_REFUSED ConnectError
```

`server.log` 原文：

```
INFO:     Started server process [38724]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:50338 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:50338 - "GET / HTTP/1.1" 200 OK
INFO:     127.0.0.1:50338 - "GET /docs HTTP/1.1" 404 Not Found
```

日志无 traceback。`STOPPED returncode=1` 是进程被 `terminate()` 打断后的退出码，不是启动失败。随后再次请求 `/health` 得到 `ConnectError`，端口已不再监听。

## 6. 安全行为探针（不改仓库）

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\probe.py
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\probe_redirect.py
```

两者退出码都是 0。数据库在 `E:\muse-bridge\work\TASK-041-quicklink\probe.db`。

要点：

- `javascript:`、`data:`、`file:`、`//evil.example`、`/\evil.example`、无协议网址：创建接口全部 400。
- `HTTP://example.com/` 被接受（201）并 302，Location 为 `HTTP://example.com/`。`urllib.parse` 会把协议折成小写再校验，所以大写协议能通过。
- 含 CR/LF 或 NUL 的网址创建返回 201，未被应用层拒绝。跳转时 Location 为 `http://example.com/%0D%0ASet-Cookie:%20x=y` 和 `http://example.com/%00.evil.example`，响应头里没有裸 CR/LF。框架 `RedirectResponse` 先做了百分号编码。
- 未登录列链接 401；登录名 `' OR 1=1 --` 返回 401；`sort=recent; DROP TABLE links` 返回 400；搜索 `%' OR 1=1 --` 返回 200 且空列表。
- `/static/../app.py`、`/static/..%2fapp.py`、`/static/%2e%2e/app.py` 均为 404，响应体不含源码。
- `/static/index.html` 200。自定义后缀 `API` 返回 400。`AbCdef` 与 `abcdef` 两条都是 201。
- 退出后原 token 访问 `/api/me` 为 401；把 `expires_at` 改成 0 后再访问也是 401。

## 7. 确认本次服务已退出

关闭后的即时结果是 `AFTER_STOP_REFUSED ConnectError`（见第 5 节）。稍后复查端口：

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\port_check.py
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\who_8000.py
netstat -ano -p tcp
Get-CimInstance Win32_Process -Filter "ProcessId=32492"
```

`port_check.py` 输出：`PORT_8000_OPEN`，`PORT_8931_CLOSED`。

`who_8000.py` 输出：`STATUS 404`，`BODY {"detail":"Not Found"}`，`SERVER uvicorn`。这不是 quicklink 的 `/health`（quicklink 返回 `{"status":"ok","app":"quicklink"}`）。

`netstat` 显示 `127.0.0.1:8000 LISTENING PID 32492`。该进程命令行是另一任务的 python：`E:\muse-bridge\work\TASK-044-...`，不是本仓库的 `app.py`。没有结束它。

## 8. 收尾重跑

未改仓库源码。审查结束后重跑全量测试。

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pytest tests/ -q
```

退出码 0。`19 passed, 1 warning in 2.51s`。警告仍是 Starlette 建议改用 `httpx2`。

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe tests\live_selftest.py
```

退出码 0。8 项全部 `[PASS]`，`共 8 项，通过 8 项`。

```
git status --porcelain
```

无输出，退出码 0。仓库工作区干净。报告在 `E:\muse-bridge\out\TASK-041-quicklink\`，没有写进仓库。
