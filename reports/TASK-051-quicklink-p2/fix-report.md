# TASK-051 修复记录

对照 `E:\muse-bridge\out\TASK-032-quicklink\review.md` 的 P2 清单。每条改动后的测试都是仓库根目录全量 pytest，解释器为 `E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe`。未改 `tests/`，未加 skip/xfail，未改断言，未改 LICENSE / UPSTREAM.md。

## P2-1 已修

- 文件：`app.py:133-135`（`validate_url` 在 `app.py:131`）
- 改法：去掉首尾空白后，若含 ASCII 控制字符（`ord(ch) < 32` 或 `ord(ch) == 127`，含 CR/LF/NUL）或反斜杠，返回 400，detail 为「网址含有非法字符」。
- 验证：`python E:\muse-bridge\work\TASK-051-quicklink-p2\run_pytest.py`，exit 0。结果行：`19 passed, 1 warning in 2.70s`
- 探针（`probe_p2.py`，exit 0）：`http://example.com/\r\n...`、含 NUL、含 `\` 均为 400；`https://example.com/ok` 为 201。

## P2-2 不改

- 位置：`app.py:284-285`
- 原因：相同新旧密码已经返回 400，并且写在更新语句之前，不会清掉 `must_change_password`。`tests/test_app.py:240` 已断言 400 且标志不变。再改一遍没有行为差。

## P2-3 不改

- 位置：`DECISIONS.md:20-22`；创建接口 `app.py` 的 `create_link` 无改密守卫
- 原因：决策写明首次改密只提示、不许把强制改密加回来。`tests/test_app.py:55` 在未改密时就创建短链。加上拦截现有测试会失败，本轮不许改测试。

## P2-4 已修

- 文件：`app.py:59-61` `hash_token`；写入 `app.py:252`；校验 `app.py:196`；退出 `app.py:269`；改密保留当前会话 `app.py:300`
- 改法：`sessions.token` 改存 `SHA-256` 十六进制。登录响应仍返回原始 token。校验、删除、改密比较都先对请求 token 做同样哈希。
- 验证：同上 pytest，exit 0。结果行：`19 passed, 1 warning in 2.76s`
- 探针：`RAW_IN_DB False`，`HASH_IN_DB True`（会话行等于 `hash_token(原始 token)`，不等于原始 token）。

## P2-5 不改

- 位置：`app.py:167` `escape_like`，`app.py:357-359` 查询带 `ESCAPE '\'`
- 原因：`%` 和 `_` 已按字面转义。`tests/test_app.py:264` 断言 `q=%` 与 `q=pop_` 返回空列表。

## P2-6 已修

- 文件：`app.py:160`（自动短码占用）、`app.py:326`（自定义后缀占用）、`app.py:462`（跳转查找）
- 改法：三处 `WHERE code = ?` 改为 `WHERE code = ? COLLATE NOCASE`。占用时仍返回 409。
- 验证：同上 pytest，exit 0。结果行：`19 passed, 1 warning in 2.61s`
- 探针：先建 `AbCdef` 返回 201，再建 `abcdef` 返回 409；`GET /ABCDEF` 为 302，`Location` 为 `https://example.com/A`。

## P2-7 已修

- 文件：`app.py:455-458`
- 改法：保留字不再 `raise HTTPException`（JSON）。改为与缺失短码相同的 HTML：`<h1>404</h1><p>这个短链不存在。</p>`，状态码 404。
- 验证：同上 pytest，exit 0。结果行：`19 passed, 1 warning in 2.58s`。`test_docs_endpoints_disabled` 只断言 `/docs`、`/redoc`、`/openapi.json` 为 404，HTML 正文不改变状态码。
- 探针：`/favicon.ico` 与 `/docs` 的 `content-type` 为 `text/html; charset=utf-8`，正文与 `/zzzzzz` 相同。

## P2-8 不改

- 位置：`static/index.html:162` 仍是 `` `${location.origin}/${l.code}` ``
- 原因：`DECISIONS.md:27-29` 写明评估后不改，审查不再复议。短码字符集是 `app.py:34` 的 `^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$`，尖括号过不了校验。长网址已在 `static/index.html:163` 走 `escapeHtml`。

## P2-9 不改

- 位置：`requirements.txt:3` `python-multipart==0.0.32`
- 原因：`app.py` 没有引用它。这不是版本冲突。任务不允许改已有依赖的版本号，删除未使用依赖也不修功能缺陷。

## P2-10 不改

- 位置：venv `fastapi\testclient.py:1` 的 `StarletteDeprecationWarning`
- 原因：全量测试仍然通过。去掉警告要换 httpx/Starlette 版本，触碰依赖版本约束。

## P2-11 已修

- 文件：`NOTES.md:28-29`
- 改法：删掉「云端 2 核 / 7.7G 内存绰绰有余（实测见 README 的测试一节）」。改为说明 README 测试一节没有核数或内存实测，此处不引用具体数字。保留单进程、SQLite、无外部服务、无 GPU 的描述。
- 验证：同上 pytest，exit 0。结果行：`19 passed, 1 warning in 2.47s`

## 最终全量 pytest

命令：`python E:\muse-bridge\work\TASK-051-quicklink-p2\run_pytest.py`（仓库根，exit 0）

```
19 passed, 1 warning in 3.02s
```

另：`tests/live_selftest.py` exit 0，`共 8 项，通过 8 项`。未计入上面的 pytest 行。

## git status --porcelain

```
 M NOTES.md
 M app.py
```
