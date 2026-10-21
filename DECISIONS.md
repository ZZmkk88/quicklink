# 决策记录（DECISIONS.md）

本仓的用户决策、复核不采纳项及其理由。审查再报已决事项时引本文件关闭，不反复复议。

## 2026-10-21 · TASK-032 审查合并

Grok 本轮报告（grok/TASK-032-quicklink，基座 == 当时 main）：P0 无，P1 两条全修，P2 十一条未改。
云端逐行核验 diff 与报告逐条对得上，测试文件未动，改动只在 app.py，予以采纳：

- **采纳 P1-1（改密吊销其他会话）**：改密成功时同事务 `DELETE FROM sessions
  WHERE user_id = ? AND token != ?`，保留本次会话。与口径第 2 条一致。
  已配回归测试（改密后旧会话 401、本次仍 200）。
- **采纳 P1-2（关闭匿名交互文档）**：`FastAPI(docs_url=None, redoc_url=None,
  openapi_url=None)`。Grok 探针证实文档页加载 jsDelivr / Google Fonts 第三方脚本，
  而登录 token 存于 localStorage，存在被盗风险。与口径第 6 条一致。
  已配回归测试（/docs、/redoc、/openapi.json 返回 404，/health 与首页仍 200）。

### P2 评估与处置

- **P2-3（默认口令不强制更换）按口径第 1 条关闭**：首次改密只提示、不强制，
  不许以任何形式（守卫/中间件/拦截器）把强制改密合回来。Grok 本轮明确不修，
  审查再报此项时直接引本条关闭。
- **P2-2（新旧密码相同也能改密）本轮已实现**：相同则 400 拒绝，且不清改密标志
  （此前同密码"改密"会把首次改密提示标志清掉）；断言测试已加。
- **P2-5（搜索词 % / _ 被当 LIKE 通配符）本轮已实现**：服务端转义后加
  `ESCAPE '\'`；断言测试已加（q=%、q=pop_ 只匹配字面）。
- **P2-8（短码拼 innerHTML）评估后不改**：短码服务端强制校验
  （2–32 位字母、数字、-、_），尖括号过不了校验；长网址前端已用 escapeHtml 转义，
  无可利用路径。
- **留待后续（本轮未采纳）**：P2-1（网址含 CR/LF/NUL 控制字符）、P2-4（会话 token
  明文入库）、P2-6（短码大小写各算一条）、P2-7（保留字短码走 JSON 404 而非 HTML 提示页）。
  均未动行为，留待后续轮次评估。

## 2026-10-21 · TASK-051 / TASK-041 合并

两轮基座均为当时 main，报告逐条核验 diff 一致，测试文件未动。

### TASK-051（review+fix）：5 项全部采纳

- ① `validate_url` 拒绝 ASCII 控制字符（码点 <32 或 ==127）与反斜杠，
  避免写进跳转 Location（原 TASK-032 的 P2-1，留待项销项）。
- ② 会话表只存 token 的 SHA-256（登录响应仍返回原始 token；
  **升级后老会话失效，需重新登录一次**）。四个触点一致：
  登录写入、current_user 校验、logout 删除、改密吊销其他会话
  （原 P2-4，留待项销项；符合口径第 7 条隐私减量、第 8 条参数化查询不硬改 compare_digest）。
- ③ 短码占用检查、跳转查找、随机码防撞三处加 `COLLATE NOCASE`
  大小写折叠（原 P2-6，留待项销项）。已知限制：UNIQUE 索引仍是二进制比较，
  应用层 409 兜底避免脏数据；建库 init 不改索引以免脏库 init 失败。
- ④ 保留字短码 404 改为与缺失短码统一的 HTML 提示页（原 P2-7，留待项销项）。
- ⑤ NOTES.md 文案修正：删掉"实测见 README 的测试一节"的不实引用
  （README 只有命令没有核数/内存数字）。
- 明确不修：强制改密（按本文件 2026-10-21 节与口径第 1 条关闭）。

### TASK-041（review）：去重后评估

与 051 按内容去重：P2-1～P2-4 已被 051 覆盖；"默认口令不强制更换"、
"短码 innerHTML" 按本文件既有条目关闭，不复议。

- **采纳**：安全响应头中间件（X-Frame-Options: DENY、
  Content-Security-Policy: frame-ancestors 'none'、
  X-Content-Type-Options: nosniff，与 taskboard 同口径）；
  `/health` 加 `SELECT 1` 查库（失败 503）；
  并发下短码唯一约束冲突捕获 `IntegrityError` 转 409
  （`_insert_link_row`，确定性单测覆盖竞态分支）。
- **不动**：httpx 的 Starlette 弃用警告、python-multipart 未被引用
  （依赖约束，不改版本）。
