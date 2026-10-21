# quicklink 验收审查

结论：服务能在本机跑通，没有 P0，也没有要改代码的 P1。pytest 19 项通过，真实流程自测 8/8 通过，`127.0.0.1:8000` 的 `/health` 与首页返回正常，进程已退出。README 的功能叙述和代码一致，差在几处没写全。许可证在「独立重写」前提下自洽；上游 commit 与版权行是否逐字，本次不能外网核对，所以不改 `LICENSE` 和 `UPSTREAM.md`。未改仓库源码。

## 本地跑通记录

环境：Windows，`python --version` 为 `Python 3.11.9`。虚拟环境在 `E:\muse-bridge\work\TASK-041-quicklink\.venv`，没有写进仓库。依赖用这份环境里的解释器安装，工作目录是仓库根目录。

本机 `py` 启动器不可用，这是环境问题，不是仓库缺陷。命令与原文：

```
py --version
```

```
Unable to create process using 'E:\python.exe --version': ???????????
```

退出码 1。随后用 `python -m venv` 建环境，没有走 README 里的 `py -m venv`。也没有执行 `Activate.ps1`，后文命令都直接调用 venv 的 `python.exe`。

安装（`requirements-dev.txt` 第一行包含 `-r requirements.txt`）：

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

退出码 0。末行包含 `Successfully installed ... fastapi-0.156.4 ... httpx-0.28.1 ... pytest-9.1.1 ... python-multipart-0.0.32 ... starlette-1.9.0 ... uvicorn-0.54.0`。与钉死版本一致，没有依赖冲突。

自动化测试：

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pytest tests/ -q
```

退出码 0。

```
...................                                                      [100%]
19 passed, 1 warning in 2.74s
```

警告原文来自已安装的 Starlette，不是失败：

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

真实流程自测：

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

该脚本监听 `8931`（`tests/live_selftest.py:16`），数据库由 `tempfile.mkdtemp` 放到系统临时目录（`tests/live_selftest.py:28`）。这是脚本自己的行为。

按 README 的端口另起一次。数据库改为 `E:\muse-bridge\work\TASK-041-quicklink\smoke.db`，避免在仓库里生成 `data/quicklink.db`。脚本 `E:\muse-bridge\work\TASK-041-quicklink\smoke_server.py`：

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\smoke_server.py
```

退出码 0。输出片段：

```
PID 32688 port 8000
GET /health -> 200 {"status":"ok","app":"quicklink"}
GET / -> 200 content-type=text/html; charset=utf-8
HOME_HAS_LOGIN True
HOME_HAS_TITLE True
GET /docs -> 404
STOPPED returncode=1
AFTER_STOP_REFUSED ConnectError
```

`server.log` 有 `Uvicorn running on http://127.0.0.1:8000`，以及这三条访问：`GET /health` 200、`GET /` 200、`GET /docs` 404。日志没有 traceback。`returncode=1` 是 `terminate()` 打断进程的退出码。打断后立刻再请求 `/health` 为 `ConnectError`，说明本次进程已经不在听端口。

稍后 `127.0.0.1:8000` 又被别的进程占用（PID 32492，命令行指向 `E:\muse-bridge\work\TASK-044-...`，`GET /health` 返回 `{"detail":"Not Found"}`）。那不是本次的 quicklink，没有结束它。

## README 与实际不符处

功能叙述和代码对得上的部分先记在这里，避免把「没写到」说成「写反了」：

- 默认账号 `admin` / `admin123`，以及 `QL_INITIAL_USERNAME`、`QL_INITIAL_PASSWORD`：`README.md:18-19`，`app.py:29-30`。
- 监听 `127.0.0.1:8000`，`QL_PORT`，默认库 `data/quicklink.db`，`QL_DB_PATH`：`README.md:39-41`，`app.py:27`，`app.py:484`。本次 8000 端口实测与此一致。
- Token 24 小时、改密吊销其他会话并保留本次、新旧密码不能相同：`README.md:9`，`app.py:28`，`app.py:276-277`，`app.py:289-293`。
- 6 位随机短码、占用返回明确错误、302 跳转、停用 410、点击记时间 / Referer / 设备大类、不存 UA 原文和 IP：`README.md:10-12` 与 `README.md:69`，`app.py:33`，`app.py:85-91`，`app.py:164-175`，`app.py:445-476`。
- 测试命令和自测流程：`README.md:48-56`。本次两条命令都跑通，流程与脚本一致。

下面是对不上或没写全的条目。

1. `README.md:9` 只写「新密码不能与旧密码相同」。`app.py:278-279` 还要求至少 6 位，不足则 400，文案是「新密码至少 6 位」。README 少了这条限制。
2. `README.md:10` 只写可以自定义后缀、被占用会报错。`app.py:34` 与 `app.py:136-143` 还要求 2–32 位、以字母或数字开头、只含字母数字和 `-` `_`，并且拒绝保留字。这些规则 README 正文没有写（页面占位符里写了长度）。
3. `README.md:56` 写自测会「逐项打勾」。`tests/live_selftest.py:24` 实际打印 `[PASS]` 或 `[FAIL]`。流程本身一致，用词不一致。
4. `README.md:58-65` 的结构清单没有写仓库里存在的 `DECISIONS.md`、`LICENSE`、`requirements.txt`、`requirements-dev.txt`、`.gitignore`。`UPSTREAM.md` 在 `README.md:65` 有列。这是清单不全，不是把某个文件的作用写错。
5. `NOTES.md:29` 写「实测见 README 的测试一节」。`README.md:43-56` 只有命令，没有 CPU、内存或耗时数字。这是 NOTES 指错了 README，不是代码行为写错。

`HTTP://example.com/` 能创建并 302（探针返回 201，Location 为 `HTTP://example.com/`）。`urllib.parse` 比较前会把协议折成小写，所以这和 `README.md:10` 附近错误文案「以 http:// 或 https:// 开头」不冲突，不单列成缺陷。

## 许可证与署名核查

结论：本仓文件之间自洽。上游那一行版权和 commit 是否逐字，没有外网证据，不改 `LICENSE` 和 `UPSTREAM.md`。

- `LICENSE:1` 为 MIT License。`LICENSE:3` 为 `Copyright (c) 2026 quicklink contributors`。`LICENSE:5-21` 是常见 MIT 授权、保留声明和免责条款，没有额外限制。
- `UPSTREAM.md:5-8` 写上游 `https://github.com/YOURLS/YOURLS`，commit `69cb963db71566e95a1eeedbd057a2e580f26028`，许可证 MIT，署名 `Copyright (c) 2009-present, The YOURLS Contributors`。
- `UPSTREAM.md:16-18` 声明代码是 Python + FastAPI + SQLite 的独立重写，没有复制上游 PHP，版权行是从上游 `LICENSE` 逐字抄进本文件的。
- 在 `*.py`、`*.html`、`*.md`、`*.txt` 中检索 `yourls`、`YOURLS`、`Ozh`、`GPL`：命中只在 `NOTES.md:3-11` 和 `UPSTREAM.md:5-8` 的说明文字里。`app.py` 和 `static/index.html` 没有 PHP 源码，也没有上游文件头。
- 独立重写只借用短码、计数、点击日志这些想法时，新作品用自己的版权行是说得通的。本仓 `LICENSE` 不写上游版权人，和「未复制源码」的声明不打架。想法本身不受版权保护。
- 任务禁止抓取外网页面，因此没有核对这个 commit 是不是 2026-10-19 的 `Update GeoIP DB`，也没有核对 `UPSTREAM.md:8` 的版权行是否与上游 `LICENSE` 逐字相同。没有确凿反证，不修改这两个文件。若该行其实不是逐字，则 `UPSTREAM.md:15` 的「逐字复制」不实，但本次不能下这个结论。

`DECISIONS.md` 里已经采纳的行为和代码一致，抽查如下：改密吊销其他会话 `app.py:289-293`；关闭 `/docs`、`/redoc`、`/openapi.json` `app.py:118-120`（本次 `GET /docs` 为 404，自动化测试 `test_docs_endpoints_disabled` 通过）；新旧密码相同则 400 `app.py:276-277`；搜索转义 `%` 和 `_` `app.py:159-161` 与 `app.py:349-354`（对应用例通过）。

## 分级修复清单

### P0

无。安装、pytest、真实流程自测、8000 端口首页和 `/health` 都跑通了。没有阻断项。

### P1

无。下面几项看过，不升到 P1，本轮不改代码。

- 默认口令 `admin123`（`app.py:29-30`，前端只提示不拦截 `static/index.html:118`）。`DECISIONS.md:20-22` 写明禁止用守卫把强制改密加回来。自动化测试也用这对账号在改密前调用接口。服务只绑定 `127.0.0.1`（`app.py:484`）。不改。
- 网址里的 CR/LF、NUL 可以入库（`app.py:126-131`）。探针里 `custom_code=crlfurl` 创建结果是 201，跳转 Location 为 `http://example.com/%0D%0ASet-Cookie:%20x=y`；NUL 那条 Location 为 `http://example.com/%00.evil.example`。已安装的 Starlette 在 `starlette/responses.py:218` 用 `quote` 写 Location，响应头里没有裸 CR/LF。当前不能拆响应头。`javascript:`、`data:`、`file:`、协议相对网址均为 400。留下作为 P2，不升 P1。
- 会话 token 明文入库（`app.py:241-245`）。`DECISIONS.md:31` 已留待。拿到数据库文件的人可以直接改 `users.password_hash`（`app.py:65-68`），只把 token 改成哈希挡不住同一个攻击者。不升 P1。
- 短码拼进 `innerHTML`（`static/index.html:162`）。`DECISIONS.md:26-29` 已关闭。短码字符集是 `app.py:34`，尖括号过不了校验。长网址和 Referer 走了 `escapeHtml`（`static/index.html:163`、`static/index.html:192`）。不升 P1。
- 未登录访问 `/api/links` 为 401；登录名 `' OR 1=1 --` 为 401；`sort` 注入为 400；搜索 `%' OR 1=1 --` 为 200 且空列表；`/static/../app.py` 与百分号编码的 `..` 均为 404 且不含源码；退出和过期 token 访问 `/api/me` 均为 401。这些探针没有打穿。

### P2

1. `app.py:126-131` 不拒绝控制字符网址。修法：`validate_url` 拒绝码点小于 32 或等于 127 的输入，再交给现有的协议检查。当前靠框架编码兜底，`DECISIONS.md:30-32` 标过留待。
2. `app.py:78` 的 `code` 唯一约束和 `app.py:451-453` 的查询都区分大小写。探针里 `AbCdef` 与 `abcdef` 都是 201。修法：写入和查找都按同一套大小写折叠，冲突返回 409。`DECISIONS.md:31` 留待。
3. `app.py:241-245` 会话 token 明文存放。修法：库里只存哈希，校验时哈希后再查。收益有限，见 P1 一节，不在本轮改。
4. `app.py:447-448` 保留字抛 JSON 404，`app.py:455-457` 普通缺失返回 HTML 404。修法：两条都返回同一份 HTML 提示页。`DECISIONS.md:31-32` 留待。
5. `app.py:317-327` 先查再插入，并发下唯一约束会变成未捕获的 `IntegrityError`。修法：捕获 `sqlite3.IntegrityError` 并返回 409。单用户场景难撞上。
6. `app.py:430-432` 的 `/health` 不访问数据库。修法：执行 `SELECT 1`，失败返回 503。现在它只说明进程活着，本次实测返回的就是 `{"status":"ok","app":"quicklink"}`。
7. `app.py:115-121` 创建应用时没有安全响应头。修法：增加 `X-Content-Type-Options: nosniff` 和 `X-Frame-Options: DENY`。服务只监听本机，点击劫持面小。
8. `README.md:9` 与 `README.md:10` 少写了密码最少 6 位和自定义后缀规则。修法：各补一句，与 `app.py:278-279`、`app.py:136-143` 对齐。纯文档，不是阻断。
9. `requirements-dev.txt:2` 的 `httpx==0.28.1` 会触发 Starlette 弃用警告，提示改用 `httpx2`。修法：等出现真正的依赖冲突再改版本。测试现在是通过的，本任务也不允许无冲突时改版本号。
10. `requirements.txt:3` 声明了 `python-multipart`，`app.py` 没有表单或上传接口，启动日志也没有缺包报错。修法：确认 FastAPI 不在导入期依赖它之后再从清单删掉。未做卸载实验，本轮不改依赖。

已决、本轮不复议：默认口令不强制更换（`DECISIONS.md:20-22`）；短码 `innerHTML` 不改（`DECISIONS.md:26-29`）。
