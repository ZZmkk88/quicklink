# TASK-051-quicklink-p2 执行记录

- 开工 2026-10-21 工作目录 E:\muse-bridge\in\TASK-051-quicklink-p2

## 基线 pytest（改代码前）

命令（经 `E:\muse-bridge\work\TASK-051-quicklink-p2\run_pytest.py`，TEMP/TMP/PYTHONPYCACHEPREFIX 与 cache_dir 都在该工作目录；解释器为上一轮已有 venv）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe -m pytest tests -q --override-ini cache_dir=E:\muse-bridge\work\TASK-051-quicklink-p2\pytest-cache
```

工作目录：`E:\muse-bridge\in\TASK-051-quicklink-p2`。exit 0。

```
...................                                                      [100%]
19 passed, 1 warning in 8.24s
```

警告：`StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` 出处 `venv\Lib\site-packages\fastapi\testclient.py:1`。

`python --version`：Python 3.11.9。`git status --porcelain` 此时为空。

## P2-1 之后 pytest

`validate_url` 拒绝 ASCII 控制字符与反斜杠后：

```
python E:\muse-bridge\work\TASK-051-quicklink-p2\run_pytest.py
```

exit 0。`19 passed, 1 warning in 2.70s`

探针（`probe_p2.py`，改 P2-4/6/7 之前）exit 0：

```
CREATE crlf status=400 body={"detail":"网址含有非法字符"}
CREATE nul status=400 body={"detail":"网址含有非法字符"}
CREATE backslash status=400 body={"detail":"网址含有非法字符"}
CREATE ok status=201
CREATE AbCdef 201
CREATE abcdef 201
GET /ABCDEF 404
GET /favicon.ico status=404 ctype=application/json body='{"detail":"短链不存在"}'
GET /docs status=404 ctype=application/json
RAW_IN_DB True
HASH_IN_DB NO_HASH_FN
```

## P2-4 之后 pytest

会话只存 SHA-256 后：exit 0。`19 passed, 1 warning in 2.76s`

## P2-6 之后 pytest

短码占用与跳转改为 `COLLATE NOCASE` 后：exit 0。`19 passed, 1 warning in 2.61s`

## P2-7 之后 pytest

保留字改为同一段 HTML 404 后：exit 0。`19 passed, 1 warning in 2.58s`

## P2-11 之后 pytest

NOTES.md 去掉不存在的实测数字后：exit 0。`19 passed, 1 warning in 2.47s`

同一时刻探针（四项都已改完）exit 0：

```
CREATE crlf status=400
CREATE nul status=400
CREATE backslash status=400
CREATE ok status=201
CREATE AbCdef 201
CREATE abcdef 409 {"detail":"这个后缀已被占用，换一个"}
GET /ABCDEF 302 https://example.com/A
GET /favicon.ico status=404 ctype=text/html; charset=utf-8 body='<h1>404</h1><p>这个短链不存在。</p>'
GET /docs status=404 ctype=text/html; charset=utf-8 body='<h1>404</h1><p>这个短链不存在。</p>'
GET /zzzzzz status=404 ctype=text/html; charset=utf-8
SESSION_ROWS 1
RAW_IN_DB False
HASH_IN_DB True
```

## 全部改完后的全量 pytest

```
python E:\muse-bridge\work\TASK-051-quicklink-p2\run_pytest.py
```

工作目录 `E:\muse-bridge\in\TASK-051-quicklink-p2`。exit 0。

```
19 passed, 1 warning in 3.02s
```

警告仍是 venv 里 Starlette 对 httpx 的 `StarletteDeprecationWarning`，不是失败。

## live_selftest（额外，本地进程，未访问外网）

```
python E:\muse-bridge\work\TASK-051-quicklink-p2\run_live.py
```

即 `E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe tests\live_selftest.py`。exit 0。

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

## git

`git diff --stat`：

```
 NOTES.md |  4 ++--
 app.py   | 26 ++++++++++++++++++--------
 2 files changed, 20 insertions(+), 10 deletions(-)
```

`git status --porcelain`（改动仍在工作区，未 commit）：

```
 M NOTES.md
 M app.py
```
