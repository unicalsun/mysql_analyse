# Changelog

## 2026-09-09 — 初版完成

### 新增
- 基于 deepagents 框架搭建 MySQL 分析智能体
- 7 个安全工具：show_databases / show_tables / describe_table / query_database / show_processlist / show_status / show_variables
- 5 个高危工具（HITL 二次确认）：execute_binlog_analysis / execute_ddl / truncate_table / execute_dml / purge_binlog
- .env 配置：MySQL 连接 + DeepSeek LLM
- 交互式 CLI 循环（agent.py + main.py）

### 修复
- GraphOutput 对象属性访问：messages 通过 `result.value["messages"]` 获取，非 `result.messages`
- config.py 中 pymysql cursorclass 使用 `pymysql.cursors.DictCursor` 类而非硬编码整数

### 已知问题
- 首次运行时 agent 自动加载内置工具（ls/read_file/write_file 等），prompt 占用约 3800 tokens
