# quicklink 修复记录

只修 review.md 清单里的 P1。没有 P0。P2 未改。

## P1-1 改密后其他会话仍然有效

- 文件：`app.py:257-285`（原 `change_password` 在 app.py:257-274，只更新用户表）
- 改法：改密成功时增加 `DELETE FROM sessions WHERE user_id = ? AND token != ?`（app.py:276-280），保留本次请求的 token，删掉该用户其余会话。
- 验证命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\verify_p1_1.py
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_pytest.py
```

- 验证输出（两条均 exit 0）：

```
login_a 200 must_change True
login_b 200
change 200 {"ok":true}
token_a_after 200 {"username":"admin","must_change_password":false}
token_b_after 401 {"detail":"登录已过期，请重新登录"}
old_password 401
new_password 200 must_change False
```

```
15 passed, 1 warning in 1.55s
```

改密所用的 token 仍有效，另一条登录会话变为 401，旧密码无法再登录。pytest 15 项通过。警告仍是 Starlette 对 httpx 的弃用提示，与本次改动无关。

## P1-2 未登录可打开交互文档并加载第三方脚本

- 文件：`app.py:115-121`（原 app.py:115 为 `app = FastAPI(title="quicklink", lifespan=lifespan)`）
- 改法：创建应用时设置 `docs_url=None`、`redoc_url=None`、`openapi_url=None`，不再提供 Swagger、ReDoc 和 OpenAPI JSON。
- 验证命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\verify_p1_2.py
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_pytest.py
```

- 验证输出（两条均 exit 0）：

```
/docs 404 application/json {"detail":"短链不存在"}
/redoc 404 application/json {"detail":"短链不存在"}
/openapi.json 404 application/json {"detail":"短链不存在"}
/health 200 application/json {"status":"ok","app":"quicklink"}
/ 200 text/html; charset=utf-8 <!DOCTYPE html> ...
```

```
15 passed, 1 warning in 1.50s
```

`/docs`、`/redoc`、`openapi.json` 不再返回文档页（这三个名字在 app.py 的保留短码里，关闭文档路由后落到短码处理，返回 404 JSON，不再包含 jsDelivr 或 Google Fonts）。`/health` 和首页仍是 200。pytest 15 项通过。

同一结论在真实 uvicorn 进程上再核对了一次（不设 `QL_PORT`，数据库在工作目录，查完即停）：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\smoke_after.py
```

输出（脚本 exit 0；服务被 terminate，进程退出码 1）：

```
GET /health status=200 body={"status":"ok","app":"quicklink"}
GET / status=200 body=<!DOCTYPE html> ...
GET /docs status=404 body={"detail":"短链不存在"}
GET /redoc status=404 body={"detail":"短链不存在"}
GET /openapi.json status=404 body={"detail":"短链不存在"}
Uvicorn running on http://127.0.0.1:8000
```

随后 `check_down.py`：`WinError 10061`，端口 8000 已拒绝连接。没有浏览器工具，页面行为用这次真实 HTTP 请求核对，没有在浏览器里点登录。

## 全量重跑

两项都改完之后重跑 README 里的两条测试。命令：

```
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_pytest.py
E:\muse-bridge\work\TASK-032-quicklink\venv\Scripts\python.exe E:\muse-bridge\work\TASK-032-quicklink\run_live.py
```

pytest（exit 0）：

```
15 passed, 1 warning in 1.54s
```

警告原文仍是：

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

这是依赖组合的提示，不是断言失败。未改测试，也未改依赖版本。

live_selftest（exit 0）：

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

没有失败项。

## git status

命令：

```
git status --porcelain
```

输出（exit 0）：

```
 M app.py
```

工作区只改了 `app.py`，改动还在，没有被还原。
