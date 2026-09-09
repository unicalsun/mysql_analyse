#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : agent.py
@Author  : Evan Sun
@Date    : 2026-09-09
@Desc    : MySQL 分析智能体 — 创建 agent 并运行交互循环
"""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from deepagents import create_deep_agent

from config import LLM_MODEL
from tools import ALL_TOOLS, DANGEROUS_TOOLS

SYSTEM_PROMPT = """你是一个 MySQL 数据库分析智能体，帮助用户分析和管理 MySQL 数据库。

你的能力：
- 查询数据库、表结构、数据内容
- 分析服务器状态、进程列表、系统变量
- 分析 binlog 二进制日志（只读分析）
- 执行 DDL（建表/改表/删表）、DML（增删改）、截断表、清理 binlog

工作原则：
1. 用户提出分析需求时，先用安全工具（query_database, show_databases 等）自主探索，收集信息后再给出结论。
2. 涉及写操作（DDL/DML/truncate/binlog 清理）时，先向用户说明操作内容和影响，再调用对应工具。
3. 对查询结果进行总结时，用中文清晰说明关键发现。
4. 如果用户的问题模糊，先用 SHOW DATABASES / SHOW TABLES 探索，再给出建议。
"""


def create_mysql_agent():
    """创建 MySQL 分析 agent，配置高危工具的二次确认。"""
    # 高危工具名称列表，用于 interrupt_on
    dangerous_tool_names = [t.name for t in DANGEROUS_TOOLS]

    checkpointer = MemorySaver()

    agent = create_deep_agent(
        model=LLM_MODEL,
        tools=ALL_TOOLS,
        system_prompt=SYSTEM_PROMPT,
        interrupt_on={name: True for name in dangerous_tool_names},
        checkpointer=checkpointer,
        name="mysql-analyst",
    )
    return agent, checkpointer


def _print_tool_call(action_request: dict):
    """打印工具调用详情，供用户确认。"""
    print("\n" + "=" * 60)
    print("⚠️  高危操作需要确认")
    print("=" * 60)
    print(f"  工具：{action_request['name']}")
    print(f"  参数：")
    for k, v in action_request.get("args", {}).items():
        # 截断过长的 SQL
        val_str = str(v)
        if len(val_str) > 200:
            val_str = val_str[:200] + "..."
        print(f"    {k}: {val_str}")
    print("=" * 60)


def run_interactive_loop():
    """运行交互式 agent 循环。"""
    agent, checkpointer = create_mysql_agent()
    config = {"configurable": {"thread_id": "mysql-analysis-session"}}

    print("MySQL 分析智能体已启动（输入 quit 退出）")
    print(f"模型：{LLM_MODEL}")
    print("-" * 40)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        try:
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                version="v2",
            )
        except Exception as e:
            print(f"\n[错误] agent 调用失败: {type(e).__name__}: {e}")
            continue

        # 处理中断（高危工具等待确认）
        while getattr(result, "interrupts", None):
            interrupt_value = result.interrupts[0].value
            action_requests = interrupt_value.get("action_requests", [])

            for ar in action_requests:
                _print_tool_call(ar)

            print("\n选项：")
            print("  [y] 批准全部  [n] 拒绝全部")
            print("  [1..N] 逐个确认（用空格分隔，如: y n y）")

            try:
                choice = input("你的决定: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n操作已取消。")
                choice = "n"

            if choice == "y":
                decisions = [{"type": "approve"} for _ in action_requests]
            elif choice == "n":
                decisions = [
                    {"type": "reject", "message": "用户拒绝了此操作。请不要重试，询问用户是否需要其他操作。"}
                    for _ in action_requests
                ]
            else:
                choices = choice.split()
                decisions = []
                for i, ar in enumerate(action_requests):
                    if i < len(choices):
                        c = choices[i]
                        if c == "y":
                            decisions.append({"type": "approve"})
                        else:
                            decisions.append({
                                "type": "reject",
                                "message": f"用户拒绝了 {ar['name']} 操作。请不要重试。",
                            })
                    else:
                        decisions.append({
                            "type": "reject",
                            "message": "用户未做出决定，默认拒绝。",
                        })

            result = agent.invoke(
                Command(resume={"decisions": decisions}),
                config=config,
                version="v2",
            )

        # 输出最终回复
        state = result.value if hasattr(result, "value") else result
        messages = state.get("messages", []) if isinstance(state, dict) else []
        for msg in reversed(messages):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                print(f"\n助手: {msg.content}")
                break
