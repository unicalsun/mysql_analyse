# MySQL 分析智能体

## 项目概述

基于 deepagents 框架 + OpenAI Function calling 实现的 MySQL 数据库分析智能体，支持自然语言与 MySQL 交互，高危操作需用户二次确认。

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | deepagents (LangChain team, v0.7.13) |
| LLM | DeepSeek V4 Flash（可通过 .env 切换） |
| 数据库驱动 | pymysql (DictCursor) |
| 运行时 | LangGraph (StateGraph) |

## 项目结构

```
openai_function_calling_mysql/
├── .env              # MySQL + LLM 配置（不入库）
├── .gitignore
├── requirements.txt
├── config.py         # 环境变量加载
├── tools.py          # 12 个工具（7 安全 + 5 高危）
├── agent.py          # Agent 创建 + 交互循环 + HITL
└── main.py           # 入口
```

## 工具分类

### 安全工具（直接执行）

| 工具 | 功能 |
|------|------|
| `show_databases()` | 列出所有数据库 |
| `show_tables(database)` | 列出指定库的表 |
| `describe_table(database, table)` | 查看表结构 |
| `query_database(sql)` | 只读 SELECT 查询 |
| `show_processlist()` | 查看当前连接 |
| `show_status()` | 服务器状态变量 |
| `show_variables()` | 系统变量配置 |

### 高危工具（需用户二次确认）

| 工具 | 功能 | 风险说明 |
|------|------|---------|
| `execute_binlog_analysis(...)` | binlog 分析 | 只读，但涉及 binlog 读取 |
| `execute_ddl(database, ddl)` | DDL 操作 | 修改数据库结构 |
| `truncate_table(database, table)` | 截断表 | 数据不可恢复 |
| `execute_dml(database, sql)` | INSERT/UPDATE/DELETE | 直接修改数据 |
| `purge_binlog(before_datetime)` | 清理 binlog | 影响基于时间点的恢复能力 |

## 确认机制

通过 deepagents 的 `interrupt_on` + `MemorySaver` checkpointer 实现：
- 高危工具被调用时 → agent 暂停 → 终端显示操作详情
- 用户可选：`[y]批准` / `[n]拒绝` / 逐个确认
- 拒绝时附带 message 反馈给 agent，避免重试

## 关键 API

```python
# 创建 agent
agent = create_deep_agent(
    model="deepseek:deepseek-v4-flash",
    tools=ALL_TOOLS,
    interrupt_on={"execute_ddl": True, ...},
    checkpointer=MemorySaver(),
)

# 调用
result = agent.invoke({"messages": [...]}, config=config, version="v2")

# 从 GraphOutput 取消息（注意不是 result.messages）
state = result.value
messages = state["messages"]
```
