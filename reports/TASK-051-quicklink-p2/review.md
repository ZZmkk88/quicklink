# quicklink 第二轮审查（P2）

结论：仓库能跑。改代码前全量 pytest 为 `19 passed, 1 warning in 8.24s`（exit 0）。没有新的 P0，也没有新的 P1。上一轮 P1-1、P1-2 已在代码和测试里。本轮按 `E:\muse-bridge\out\TASK-032-quicklink\review.md` 的 P2 顺序处理：修好仍开放的 5 条（P2-1、P2-4、P2-6、P2-7、P2-11）；已实现或已写明不修的 6 条不动。

## 证据

基线命令（解释器 `E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe`，工作目录仓库根，缓存与 TEMP 在 `E:\muse-bridge\work\TASK-051-quicklink-p2`）：

```
19 passed, 1 warning in 8.24s
```

警告原文来自 venv 的 `fastapi\testclient.py:1`：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 19 条断言都过了。`python --version` 为 Python 3.11.9。改前 `git status --porcelain` 为空。

P1 已在树里，本轮未再改行为：

- P1-1 改密吊销其他会话：`app.py:297-300`，`DELETE FROM sessions WHERE user_id = ? AND token != ?`。回归测试 `tests/test_app.py:219` `test_change_password_revokes_other_sessions`。
- P1-2 关闭匿名文档：`app.py:123-125` `docs_url=None`、`redoc_url=None`、`openapi_url=None`。回归测试 `tests/test_app.py:255`。

`DECISIONS.md:10-16` 记录这两项已采纳。`DECISIONS.md:3` 写明已决事项不再复议。

## 上一轮 P2 对照

| 编号 | 开工时状态 | 本轮 |
| --- | --- | --- |
| P2-1 | `validate_url` 只查 scheme/netloc，CR/LF、NUL、反斜杠能入库 | 修 |
| P2-2 | `app.py:284-285` 新旧相同返回 400；`tests/test_app.py:240` 已覆盖 | 不改 |
| P2-3 | `DECISIONS.md:20-22` 关闭；未改密即可建链，见 `tests/test_app.py:55` | 不改 |
| P2-4 | 登录把原始 token 写入 `sessions` | 修 |
| P2-5 | `escape_like` + `ESCAPE '\'`；`tests/test_app.py:264` 已覆盖 | 不改 |
| P2-6 | 占用和跳转都是 `code = ?`，大小写各算一条 | 修 |
| P2-7 | 保留字 `HTTPException` JSON 404，缺失短码 HTML 404 | 修 |
| P2-8 | `DECISIONS.md:27-29` 评估后不改；`static/index.html:162` 仍直接拼短码 | 不改 |
| P2-9 | `requirements.txt:3` 的 `python-multipart` 在 `app.py` 无引用 | 不改 |
| P2-10 | 收集测试时的 StarletteDeprecationWarning | 不改 |
| P2-11 | `NOTES.md` 写「云端 2 核 / 7.7G……实测见 README 的测试一节」，README 测试节只有命令 | 修 |

LICENSE、UPSTREAM.md 本轮未改。上一轮本地核对未发现可改的事实错误；上游 commit 说明与时间仍未联网复核，标未核实。

## 分级修复清单

### P0

无。基线 pytest 19 项通过。没有跑不起来的阻断项。

### P1

无新项。P1-1、P1-2 已在 `app.py:123-125` 与 `app.py:297-300`，并有回归测试。

### P2

1. P2-1 跳转目标接受控制字符和反斜杠。文件 `app.py:131-137`（修前只有 scheme/netloc 检查）。修法：`strip` 之后若含 ASCII 控制字符（`ord < 32` 或 `127`）或 `\`，返回 400。
2. P2-2 不修。`app.py:284-285` 已经拒绝相同密码，且在拒绝前返回，不会把 `must_change_password` 清掉。
3. P2-3 不修。`DECISIONS.md:20-22` 规定只提示、不强制。`tests/test_app.py:55` 在未改密时就创建短链，加守卫会让现有测试失败。本轮不许改测试。
4. P2-4 会话 token 明文入库。文件 `app.py:59-61` 及登录、校验、退出、改密四处比较。修法：库存 SHA-256，请求里的 token 先做同样哈希再查。
5. P2-5 不修。`app.py:167` `escape_like`，`app.py:357-359` 已 `ESCAPE '\'`。
6. P2-6 短码大小写各算一条。文件 `app.py:160`、`app.py:326`、`app.py:462`。修法：生成占用、自定义占用、跳转查找都改为 `code = ? COLLATE NOCASE`。
7. P2-7 保留字走 JSON 404。文件 `app.py:455-458`。修法：返回与缺失短码相同的 `<h1>404</h1><p>这个短链不存在。</p>`，状态码仍是 404。
8. P2-8 不修。`DECISIONS.md:27-29` 已关闭。短码正则 `app.py:34` 只允许字母、数字、`-`、`_`，尖括号进不了 `innerHTML` 的短码位置。
9. P2-9 不修。未使用的 `python-multipart==0.0.32` 不是依赖冲突。任务不允许改已有依赖版本，删除这一行也不在本轮缺陷修复里。
10. P2-10 不修。警告来自已安装的 Starlette，测试仍 19 passed。消除警告要改依赖版本。
11. P2-11 `NOTES.md:28-29` 引用 README 里不存在的核数和内存实测。修法：删掉这组数字和「实测见 README」，保留「单进程 + SQLite、无外部服务、无 GPU」这句（交互文档已在 `app.py:123-125` 关闭，`static/index.html` 无外链脚本）。

已知限制，未再加代码：`links.code` 的 UNIQUE 仍是二进制比较。接口层已挡住大小写重复；库外直接插入的旧重复行，跳转 `fetchone` 只取一行。给 `lower(code)` 加唯一索引可能让已有脏库在 `init_db` 失败，所以没加。已有明文会话在升级后对不上哈希，需要重新登录。
