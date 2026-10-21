# quicklink 修复报告

结论：审查清单里没有 P0，也没有要改代码的 P1。本轮没有修改仓库源码。P2 和 `DECISIONS.md` 已关闭项按任务要求不修。下面逐条说明。全量测试在文末重跑。

## 未改项

### 无编号 · P0

没有跑不起来或阻断的问题，所以没有对应改动。

依据：`pytest tests/ -q` 为 `19 passed, 1 warning in 2.74s`；`tests/live_selftest.py` 为 8 项全部 `[PASS]`；`127.0.0.1:8000` 上 `GET /health` 为 `200 {"status":"ok","app":"quicklink"}`，`GET /` 为 200 且正文含登录页。命令原文见 `run.md` 第 3–5 节。

### 不升 P1 · 默认口令

- 文件：`app.py:29-30`，`static/index.html:118`，决策 `DECISIONS.md:20-22`
- 不改原因：决策写明首次改密只提示、不许用守卫把强制改密加回来。现有测试在改密前使用 `admin` / `admin123` 调接口。服务只绑定 `127.0.0.1`（`app.py:484`）。改默认口令或加拦截会直接顶上这些约束。
- 验证：未改代码。既有用例 `test_login_ok_must_change_flag` 与创建短链用例在第一次全量测试中已通过。

### 不升 P1 · 控制字符网址

- 文件：`app.py:126-131`
- 不改原因：可以入库，但当前跳转不会把裸 CR/LF 写进响应头。已安装 Starlette `responses.py:218` 对 Location 做 `quote`。这是 P2，不是已经打穿的响应拆分。
- 验证命令：

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe E:\muse-bridge\work\TASK-041-quicklink\probe_redirect.py
```

- 真实输出片段：

```
--- crlfurl status 302
location repr 'http://example.com/%0D%0ASet-Cookie:%20x=y'
--- nulurl status 302
location repr 'http://example.com/%00.evil.example'
```

`javascript:`、`data:`、`file:`、`//evil.example` 在 `probe.py` 里都是 400。

### 不升 P1 · 会话 token 明文

- 文件：`app.py:241-245`；`DECISIONS.md:31` 已留待
- 不改原因：数据库被拷走时，攻击者可以改 `users.password_hash`（`app.py:65-68`），只哈希 token 挡不住同一次泄露。不升 P1，本轮不改。
- 验证：未改代码。过期 token 的探针结果是 401（`probe.py`：`expired token rejected`）。

### 不升 P1 · 短码写入 innerHTML

- 文件：`static/index.html:162`；`DECISIONS.md:26-29` 已关闭
- 不改原因：短码必须匹配 `app.py:34`，不能含 `<`。长网址和 Referer 已走 `escapeHtml`。没有可利用路径，决策也明确不改。
- 验证：未改代码。`test_custom_code_invalid_and_reserved` 在全量测试中通过，非法后缀为 400。

### P2 一律不改

清单 P2-1 至 P2-10 都不是阻断，也不是已经打穿的安全或数据问题。任务只允许修 P0 和 P1，且最多 5 项。这里一项都没改。`requirements.txt` 与 `requirements-dev.txt` 的版本号未动。`LICENSE` 与 `UPSTREAM.md` 未动（上游事实未能外网核实，没有确凿错误）。测试文件未动。

## 收尾全量测试

审查结束后重跑，没有改测试、没有改断言。两条都通过，没有失败项。

```
E:\muse-bridge\work\TASK-041-quicklink\.venv\Scripts\python.exe -m pytest tests/ -q
```

退出码 0。

```
...................                                                      [100%]
============================== warnings summary ===============================
..\..\work\TASK-041-quicklink\.venv\Lib\site-packages\fastapi\testclient.py:1
  E:\muse-bridge\work\TASK-041-quicklink\.venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
19 passed, 1 warning in 2.51s
```

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

那条 Starlette 警告仍在，测试没有失败。没有改 `requirements-dev.txt`。

## git status

仓库源码本轮没有改过，所以工作区是干净的。这不是改动丢失：没有执行过 `git checkout`、`git restore`、`git stash` 或 `git clean`，也没有手工还原文件。报告写在 `E:\muse-bridge\out\TASK-041-quicklink\`，不在这个 git 仓库里。

命令与输出原样如下。标准输出为空，退出码 0。

```
git status --porcelain
```

标准输出：

```
```

（以上代码块内没有任何字符。）
