# quicklink 验收

结论：仓库能在本机跑通。pytest 15 项通过，`live_selftest.py` 8/8 通过，`127.0.0.1:8000` 的 `/` 与 `/health` 均返回 200，服务已关掉。没有 P0。P1 两项：改密不使其他会话失效；默认开放 `/docs`、`/redoc`、`/openapi.json`，文档页加载第三方脚本。本次只修这两项。

## 本地跑通记录

本机 `py -3 --version` 失败（exit 1）：`Unable to create process using 'E:\python.exe --version'`。`python --version` 为 Python 3.11.9。README 的 Windows 段写 `py -m venv`，这里是启动器坏了，记为环境限制，不是代码缺陷。虚拟环境放在 `E:\muse-bridge\work\TASK-032-quicklink\venv`，没有写进待审仓库。

运行依赖（exit 0）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe -m pip install -r E:\muse-bridge\in\TASK-032-quicklink\requirements.txt
Successfully installed ... fastapi-0.156.4 ... python-multipart-0.0.32 ... uvicorn-0.54.0
```

开发依赖（exit 0）：`httpx-0.28.1`、`pytest-9.1.1` 已装上。

pytest（exit 0，工作目录为仓库，缓存和 TEMP 在工作目录）：

```
15 passed, 1 warning in 1.74s
```

警告原文：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 来自已安装的 Starlette，15 项断言都过了。

`python tests/live_selftest.py`（exit 0）：

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

按 README 起服务：不设 `QL_PORT`，数据库放到工作目录。`smoke_server.py` 输出：

```
GET /health status=200 body: {"status":"ok","app":"quicklink"}
GET / status=200 content-type: text/html; charset=utf-8
stderr: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

首页正文含 `<title>quicklink · 短链工坊</title>`。进程 terminate 后退出码 1（主动停，不是启动失败）。随后 `check_down.py`：

```
DOWN /health URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。>
```

额外探针（`probe_defects.py`、`probe_docs.py`，均 exit 0）里和缺陷直接相关的片段：

- `javascript:alert(1)` 创建短链返回 400。
- 含 CR/LF 的网址被接受，跳转 `Location` 为 `http://example.com/%0D%0ASet-Cookie:%20x=1`（已百分号编码，不是拆成两行头）。
- 含 NUL 的网址被接受，`Location` 为 `http://example.com%00.evil.com`。
- 改密成功后，旧 token 再请求 `/api/me` 仍是 200。退出登录后同一 token 为 401。
- `sort=recent; DROP TABLE links` 返回 400。`q=' OR 1=1 --` 返回 200 且 body 为 `[]`（参数化查询，没有注入成功）。
- 未带登录头：`/docs` 200，内含 `https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js`；`/redoc` 200，内含 `https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js` 和 `https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700`；`/openapi.json` 200，5993 字节。

没有遇到必须访问外网才能通过的测试，没有「环境限制」类失败。完整命令在 `run.md`。

## README 与实际不符处

按 README 在项目根目录执行时，功能描述和代码一致：默认账号 `admin` / `admin123`（README.md:18，app.py:29-30）、Token 24 小时（README.md:9，app.py:28）、6 位短码与占用 409（README.md:10，app.py:33、app.py:297-298）、302 / 停用 410（README.md:11，app.py:434-452）、点击记录字段与最近 20 条（README.md:12，app.py:379-398）、`127.0.0.1:8000`（README.md:39，app.py:460）、`QL_PORT` / `QL_DB_PATH`（README.md:40-41，app.py:27、app.py:460）。下面只列对得上的差异。

1. README.md:40 写数据库默认在 `data/quicklink.db`，读起来像相对当前工作目录。app.py:26-27 实际是 `Path(__file__).resolve().parent / "data" / "quicklink.db"`，锚在 `app.py` 所在目录。在项目根目录启动时两条路径重合；换目录执行 `python <其他路径>\app.py` 时不一致。
2. README.md:13 写按创建时间排序。app.py:322 的 `recent` 是 `ORDER BY id DESC`，不是 `created_at`。没有改写 `created_at` 的接口，所以顺序和创建顺序相同。这是排序键不一致，当前界面看不出差别。
3. README.md:18 写「首次登录会提示改密」。static/index.html:118 是每次登录成功且 `must_change_password` 仍为真都 `alert`，不是只提示第一次。app.py:101 把初始用户标成必须改密，改密成功前标志一直为 1（app.py:267）。
4. README.md:60-65 的项目结构没有列出仓库里实际有的 `requirements.txt`、`requirements-dev.txt`、`LICENSE`、`.gitignore`。
5. README 全文没有写 `GET /health`。app.py:406-408 提供该接口，tests/live_selftest.py:46 依赖它。属于遗漏，不是写反。
6. README 没有写框架默认开放文档站。app.py:115 的 `FastAPI(...)` 未关闭 `docs_url` / `redoc_url` / `openapi_url`。未登录访问这三条路径均返回 200，见上面的探针。

相关文档（不是 README 正文，但和「实际」对不上）：

- NOTES.md:28-29 写「无外部服务」，并称「云端 2 核 / 7.7G……实测见 README 的测试一节」。README.md:43-56 只有测试命令，没有这组数字。`/docs` 与 `/redoc` 的 HTML 会引用 jsDelivr、Google Fonts、fastapi.tiangolo.com。主界面 static/index.html 没有外链脚本。

## 许可证与署名核查

结论：仓库里的许可证和署名互相一致。没有发现可以在本地确证的事实错误，所以不改 `LICENSE` 和 `UPSTREAM.md`。上游 commit、提交说明、提交时间本次未联网复核，标「未核实」。

- LICENSE:1-3 是 MIT，版权行为 `Copyright (c) 2026 quicklink contributors`。LICENSE:5-21 是标准 MIT 授权与免责条款，文本完整。
- UPSTREAM.md:5-8 写上游 `https://github.com/YOURLS/YOURLS`，commit `69cb963db71566e95a1eeedbd057a2e580f26028`，许可证 MIT，署名 `Copyright (c) 2009-present, The YOURLS Contributors`。
- UPSTREAM.md:12-16 称该 commit 是 2026-10-21 通过 GitHub 接口看到的默认分支 HEAD，说明为 "Update GeoIP DB"，时间 2026-10-19，并且版权行逐字来自上游 LICENSE。本任务禁止抓取外部页面，commit、说明、时间、是否逐字一致，均为未核实。
- UPSTREAM.md:17-18 称代码是独立重写，没有复制上游 PHP。仓库内只有 `app.py`、`static/index.html`、`tests/`、依赖文件和上述文档，没有 PHP 文件，也没有 YOURLS 源码树。这一点和声明相符。
- README.md:5 指向 UPSTREAM.md，和上面一致。两份许可证都是 MIT，不冲突。独立重写不把上游版权行写进本仓库 LICENSE，和「未复制源码」一致。

## 分级修复清单

### P0

无。上面三组运行（pytest、live_selftest、8000 端口首页与健康检查）都成功，没有跑不起来的阻断项。

### P1

1. P1-1 改密后其他会话仍然有效。文件 app.py:257-274：`change_password` 只更新 `users` 的口令哈希，不删除 `sessions`。探针：改密返回 200 后，旧 token 请求 `/api/me` 仍是 200。修法：改密提交成功时删掉该用户除当前 token 以外的会话行。
2. P1-2 未登录即可打开交互文档，文档页在应用源上加载第三方脚本。文件 app.py:115。探针：`/docs`、`/redoc`、`/openapi.json` 均 200；脚本地址见上文 jsDelivr / Google Fonts。主界面把 token 放在 `localStorage`（static/index.html:102），第三方脚本若被调包就能读这个 token。修法：创建 FastAPI 时关闭 `docs_url`、`redoc_url`、`openapi_url`。

### P2

不在本次修改范围内。

1. P2-1 跳转目标接受控制字符。文件 app.py:120-125。含 CR/LF、NUL 的网址返回 201；Starlette 把它们编进单个 `Location`，本次没有看到原始响应拆分。修法：拒绝 ASCII 控制字符，并拒绝反斜杠。
2. P2-2 新旧密码相同也会成功，并把 `must_change_password` 清掉。文件 app.py:261-267。探针：用 `admin123` 改成 `admin123` 返回 200，随后 `/api/me` 里该标志为 false。修法：新旧相同则返回 400。
3. P2-3 默认口令不强制更换，标志为真时写接口仍可用。文件 app.py:29-30、app.py:287。不修：README.md:18 只要求提示；tests/test_app.py 在未改密时就调用创建短链。强制拦截会让现有测试失败。
4. P2-4 会话 token 明文写入 `sessions`。文件 app.py:231-233。修法：只存 token 的哈希，校验时对请求里的 token 做同样哈希。
5. P2-5 搜索词里的 `%`、`_` 被当成 LIKE 通配符。文件 app.py:325-330。探针：`q=%` 返回多条记录。已登录用户本来就能列出自己的全部短链，没有越权。修法：转义 `%` 和 `_`。
6. P2-6 短码大小写各算一条。文件 app.py:294-296 与 app.py:427-428。探针：`AbCdef` 与 `abcdef` 同时创建成功，分别跳到不同网址。修法：占用检查和跳转查找都按大小写不敏感处理。
7. P2-7 保留字走 JSON 404，普通缺失短码走 HTML 404。文件 app.py:423-433。`/favicon.ico` 探针 body 为 `{"detail":"短链不存在"}`。修法：保留字也返回同一段 HTML 提示页。
8. P2-8 短码直接拼进 `innerHTML`。文件 static/index.html:162。当前短码字符集过不了尖括号，探针里 `has.dot`、`bad code` 都被 400 拒绝。修法：和网址一样走 `escapeHtml`。
9. P2-9 `requirements.txt:3` 的 `python-multipart` 在 `app.py` 中没有引用。修法：从依赖清单去掉。本次不改，因为不存在依赖冲突，任务不允许改已有版本号，删除依赖也不在 P0/P1 里。
10. P2-10 测试收集时的 `StarletteDeprecationWarning`（httpx 0.28.1 与当前 Starlette）。修法会碰到依赖版本，本次不改。
11. P2-11 NOTES.md:28-29 的「无外部服务」和「README 里有资源实测」与仓库现状不符。修法：改 NOTES 的这两句，不要再引用不存在的实测数字。
