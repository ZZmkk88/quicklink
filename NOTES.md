# 调研笔记（quicklink）

2026-10-21，通过 GitHub 接口通读上游 YOURLS（HEAD 69cb963d）后记录。

## 上游的设计要点（查到的事实）

- 定位：自托管短链接脚本集（PHP），卖点是数据自控、详细统计、插件生态。
- 数据模型三张表（user/config-sample.php 里写明表前缀 `yourls_`）：
  - `yourls_url`：短码（keyword）、原网址、标题、创建时间、创建 IP、点击数（clicks 列直接计数）；
  - `yourls_log`：每次点击一行——时间、来源（referrer）、UA、IP、短码；
  - `yourls_options`：站点配置。
- 新增短链流程（includes/functions-shorturls.php）：可自动生成 keyword，也可指定；
  生成后即写入 url 表，clicks 从 0 起。
- 跳转即记账：访问短码时先落一条 log 并给 clicks +1，再 302 跳走。

## 本项目的取舍（设计决定）

- 沿用"链接表 + 点击日志表"两表结构：links（code/url/active/clicks/created_at）、
  clicks（link_id/clicked_at/referer/ua_class），计数列与逐条日志并存——
  列表页读计数列够快，统计明细查日志表。
- 短码：自动生成 6 位随机码（字母+数字，62^6 ≈ 568 亿组合，碰撞重试）；
  自定义后缀 2–32 位，字母数字与 - _，占用返回 409，系统路径（api/static 等）保留禁用。
- 隐私减量：点击日志只存 UA 的大类（桌面浏览器/移动端/机器人/其他），不存 UA 原文，
  也不存访客 IP——自用场景够用，少留个人信息。
- 停用语义：停用的短链跳转返回 410 提示页，不记点击；不存在的短码返回 404 提示页。
- 技术栈：沿用本团队已验证的轻量栈（FastAPI + SQLite + 原生单页前端），
  登录沿用既有做法（pbkdf2 密码哈希、Token 24 小时、首次登录提示改密）。
- 资源核对：单个 Python 进程 + SQLite 文件，无外部服务、无 GPU 需求。
  README 的测试一节只有命令，没有核数或内存的实测数字，这里不引用具体数字。
