# TASK-032-quicklink 执行记录

开工：2026-10-21。工作目录 `E:\muse-bridge\in\TASK-032-quicklink`。先读仓库再装环境、跑测试、起服务。

## 0. 环境探测

命令：

```
py -3 --version
```

输出（exit 1）：

```
Unable to create process using 'E:\python.exe --version': ???????????
```

命令：

```
python --version
```

输出（exit 0）：

```
Python 3.11.9
```

说明：README Windows 段写的是 `py -m venv`。本机 `py` 启动器指向损坏的 `E:\python.exe`，属环境限制。后续改用 `python`（3.11.9）在工作目录建 venv，不把 `.venv` 写进待审仓库。

## 1. 创建虚拟环境

命令：

```
python -m venv E:\muse-bridge\work\TASK-032-quicklink\venv
```

输出：无标准输出，exit 0。解释器：`E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe`。

## 2. 安装运行依赖

按 README：`pip install -r requirements.txt`（用 venv 的 python，未激活 PowerShell 执行策略）。

命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-032-quicklink\requirements.txt
```

输出摘要（exit 0）：

```
Successfully installed annotated-doc-0.0.5 annotated-types-0.8.0 anyio-4.15.1 click-8.5.0 fastapi-0.156.4 h11-0.16.0 idna-3.20 opentelemetry-api-1.45.1 pydantic-2.14.1 pydantic-core-2.50.1 python-multipart-0.0.32 starlette-1.9.0 typing-extensions-4.16.0 typing-inspection-0.4.4 uvicorn-0.54.0
```

版本与 requirements.txt 一致：fastapi==0.156.4、uvicorn==0.54.0、python-multipart==0.0.32。

## 3. 安装开发依赖

命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-032-quicklink\requirements-dev.txt
```

输出摘要（exit 0）：

```
Successfully installed certifi-2026.10.19 colorama-0.4.6 httpcore-1.0.9 httpx-0.28.1 iniconfig-2.3.1 packaging-26.3 pluggy-1.7.0 pygments-2.21.0 pytest-9.1.1
```

httpx==0.28.1、pytest==9.1.1 与 requirements-dev.txt 一致。

## 4. 自动化测试 pytest

临时目录设到 `E:\muse-bridge\work\TASK-032-quicklink\tmp`（避免测试里的 tempfile 落到系统 TEMP）。`PYTHONDONTWRITEBYTECODE=1`。pytest 缓存放到工作目录。

命令：

```
$env:TEMP='E:\muse-bridge\work\TASK-032-quicklink\tmp'
$env:TMP='E:\muse-bridge\work\TASK-032-quicklink\tmp'
$env:PYTHONDONTWRITEBYTECODE='1'
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe -m pytest tests/ -q -o cache_dir=E:\muse-bridge\work\TASK-032-quicklink\pytest-cache
```

工作目录：`E:\muse-bridge\in\TASK-032-quicklink`

实际通过辅助脚本启动（脚本只设 TEMP/TMP/PYTHONDONTWRITEBYTECODE 再调用上述 pytest，脚本本身在工作目录）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_pytest.py
```

输出（exit 0）：

```
...............                                                          [100%]
============================== warnings summary ===============================
..\..\work\TASK-032-quicklink\venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-032-quicklink\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
15 passed, 1 warning in 1.74s
```

15 项全部通过。警告来自已安装的 Starlette/FastAPI，不是测试失败。未改测试。

## 5. 真实流程自测 live_selftest.py

命令（同样经工作目录辅助脚本设置 TEMP/TMP）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\in\TASK-032-quicklink\tests\live_selftest.py
```

工作目录：`E:\muse-bridge\in\TASK-032-quicklink`

实际命令（辅助脚本只设置 TEMP/TMP/PYTHONDONTWRITEBYTECODE，再调用上面的 live_selftest）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_live.py
```

输出（exit 0）：

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

## 6. 按 README 起服务（默认端口 8000）

未设置 `QL_PORT`（代码默认 8000）。数据库改到工作目录，避免在仓库里留下 `data/quicklink.db`（禁止使用 del/rm 清理）。未使用 curl/wget，用 urllib。

命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\smoke_server.py
```

输出摘要（脚本自身 exit 0；服务进程被 terminate 后退出码 1，属主动停止）：

```
PID 26124 QL_DB_PATH=E:\muse-bridge\work\TASK-032-quicklink\smoke\quicklink.db QL_PORT unset (expect 8000)
GET /health status=200 final_url=http://127.0.0.1:8000/health
body: {"status":"ok","app":"quicklink"}
GET / status=200 final_url=http://127.0.0.1:8000/
content-type: text/html; charset=utf-8
body 开头含: <title>quicklink · 短链工坊</title>
stderr: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
stdout: "GET /health HTTP/1.1" 200 OK
stdout: "GET / HTTP/1.1" 200 OK
stopped exit=1
```

关掉后再探端口：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\check_down.py
```

输出（exit 0）：

```
DOWN /health URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```

端口 8000 已拒绝连接，服务已停。

## 7. 缺陷探针（TestClient，数据库在工作目录）

命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\probe_defects.py
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\probe_docs.py
```

与清单相关的输出片段（两条命令均 exit 0）：

```
== create 'javascript:alert(1)'
status=400

== create 'http://example.com/\r\nSet-Cookie: x=1'
status=201
== redirect location='http://example.com/%0D%0ASet-Cookie:%20x=1'

== create 含 NUL 的网址
status=201
== redirect location='http://example.com%00.evil.com'

== change to second456
status=200
== old token after real password change
status=200 body='{"username":"admin","must_change_password":false}'

== token after logout
status=401

== sort injection
status=400 body='{"detail":"sort 只能是 recent 或 clicks"}'

== q injection
status=200 body='[]'

== q wildcard percent
status=200（返回了多条短链，% 被当成 LIKE 通配）
```

`probe_docs.py`：

```
== /docs status=200 bytes=1008
https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js
https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css
https://fastapi.tiangolo.com/img/favicon.png

== /redoc status=200 bytes=890
https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js
https://fastapi.tiangolo.com/img/favicon.png
https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700

== /openapi.json status=200 bytes=5993
```

三条都未带登录头。

耗时：pytest 输出自带 `1.74s`。pip、live_selftest、起服务未单独计时，结果以上面的 exit code 为准。

## 8. 修复后的全量重跑

只改了 `app.py` 的两处 P1（改密作废其他会话；关闭 /docs、/redoc、/openapi.json）。细节在 fix-report.md。

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_pytest.py
```

输出（exit 0）：`15 passed, 1 warning in 1.54s`

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_live.py
```

输出（exit 0）：8 项全部 PASS，`共 8 项，通过 8 项`。

## 9. 修复后再起一次服务

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\smoke_after.py
```

输出摘要（脚本 exit 0，服务 terminate 后进程退出码 1）：

```
GET /health status=200 body={"status":"ok","app":"quicklink"}
GET / status=200 body=<!DOCTYPE html> ...
GET /docs status=404 body={"detail":"短链不存在"}
GET /redoc status=404 body={"detail":"短链不存在"}
GET /openapi.json status=404 body={"detail":"短链不存在"}
stderr: Uvicorn running on http://127.0.0.1:8000
```

`check_down.py`：`WinError 10061`，8000 已拒绝连接。

