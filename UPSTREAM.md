# 上游溯源（UPSTREAM）

本项目在设计阶段学习了开源社区短链接工具的通行思路，按接力规范记录上游信息如下：

- **source_url**: https://github.com/YOURLS/YOURLS
- **source_commit**: 69cb963db71566e95a1eeedbd057a2e580f26028
- **license**: MIT
- **attribution**: Copyright (c) 2009-present, The YOURLS Contributors

## 说明

- `source_commit` 是 2026-10-21 通过 GitHub 接口实查的上游默认分支 HEAD 提交
  （提交说明 "Update GeoIP DB"，提交时间 2026-10-19）；当日做设计调研时查阅的
  上游内容正是这一提交，包括 README、user/config-sample.php（数据表命名）、
  includes/functions-shorturls.php（新增短链的流程）与 LICENSE 原文。
- `attribution` 的版权行逐字复制自上游仓库 `LICENSE` 原文，未做任何改动。
- 本项目代码为独立重写（Python + FastAPI + SQLite），未复制上游（PHP）源码；
  借鉴的是短码、点击计数与点击日志这类核心概念，具体调研记录见 NOTES.md。
