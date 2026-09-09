#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : tools.py
@Author  : Evan Sun
@Date    : 2026-09-09
@Desc    : MySQL 工具定义（安全工具 + 高危工具）
"""

import json
import pymysql
from langchain_core.tools import tool
from config import MYSQL_CONFIG


def _get_conn(database: str = "") -> pymysql.Connection:
    cfg = {**MYSQL_CONFIG}
    if database:
        cfg["database"] = database
    return pymysql.connect(**cfg)


def _format_rows(rows: list[dict]) -> str:
    if not rows:
        return "(empty result)"
    return json.dumps(rows, ensure_ascii=False, default=str, indent=2)


# ============================================================
# 安全工具（直接执行，无需确认）
# ============================================================

@tool
def query_database(sql: str) -> str:
    """执行 SELECT 查询并返回结果。只能用于只读查询，不可执行写操作。"""
    sql_stripped = sql.strip().rstrip(";").upper()
    if not sql_stripped.startswith("SELECT") and not sql_stripped.startswith("SHOW") \
            and not sql_stripped.startswith("DESCRIBE") and not sql_stripped.startswith("EXPLAIN"):
        return "错误：query_database 只能执行只读查询（SELECT/SHOW/DESCRIBE/EXPLAIN），请使用对应工具执行写操作。"
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询执行失败：{e}"
    finally:
        conn.close()


@tool
def show_databases() -> str:
    """列出 MySQL 实例上所有数据库。"""
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SHOW DATABASES")
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


@tool
def show_tables(database: str) -> str:
    """列出指定数据库中的所有表。"""
    try:
        conn = _get_conn(database)
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


@tool
def describe_table(database: str, table: str) -> str:
    """查看指定表的结构（列名、类型、索引等）。"""
    try:
        conn = _get_conn(database)
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(f"DESCRIBE `{table}`")
            columns = cur.fetchall()
            cur.execute(f"SHOW CREATE TABLE `{table}`")
            create_info = cur.fetchone()
        result = {
            "columns": columns,
            "create_table_sql": create_info.get("Create Table", "") if create_info else "",
        }
        return _format_rows([result])
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


@tool
def show_processlist() -> str:
    """查看当前 MySQL 所有连接和进程（相当于 SHOW FULL PROCESSLIST）。"""
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SHOW FULL PROCESSLIST")
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


@tool
def show_status() -> str:
    """查看 MySQL 服务器状态变量（Global 和 Session 级别）。"""
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SHOW GLOBAL STATUS")
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


@tool
def show_variables() -> str:
    """查看 MySQL 系统变量配置。"""
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("SHOW GLOBAL VARIABLES")
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"查询失败：{e}"
    finally:
        conn.close()


# ============================================================
# 高危工具（需要用户二次确认）
# ============================================================

@tool
def execute_binlog_analysis(
    database: str,
    start_file: str = "",
    stop_file: str = "",
    start_pos: int = 0,
    stop_pos: int = 0,
) -> str:
    """分析 MySQL binlog（二进制日志）。可指定起止文件名和位置，用于审计数据变更历史。
    此操作为只读分析，但涉及 binlog 读取，请确认后执行。"""
    parts = ["SHOW BINLOG EVENTS"]
    if start_file:
        parts.append(f"IN '{start_file}'")
    clauses = []
    if start_pos > 0:
        clauses.append(f"LIMIT {start_pos}, 1000")
    sql = " ".join(parts) + (" " + " ".join(clauses) if clauses else " LIMIT 1000")
    try:
        conn = _get_conn()
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        return _format_rows(rows)
    except Exception as e:
        return f"binlog 分析失败：{e}"
    finally:
        conn.close()


@tool
def execute_ddl(database: str, ddl_statement: str) -> str:
    """执行 DDL 语句（CREATE TABLE, ALTER TABLE, DROP TABLE, RENAME TABLE 等）。
    ⚠️ 危险操作：会修改数据库结构，请确认后执行。"""
    sql_upper = ddl_statement.strip().upper()
    allowed_prefixes = ("CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE")
    if not any(sql_upper.startswith(p) for p in allowed_prefixes):
        return f"错误：该语句不是合法的 DDL 语句。允许的操作：{allowed_prefixes}"
    try:
        conn = _get_conn(database)
        with conn.cursor() as cur:
            cur.execute(ddl_statement)
        return f"DDL 执行成功：{ddl_statement}"
    except Exception as e:
        return f"DDL 执行失败：{e}"
    finally:
        conn.close()


@tool
def truncate_table(database: str, table: str) -> str:
    """截断指定表（清空所有数据并重置自增 ID）。
    ⚠️ 高危操作：数据不可恢复，请确认后执行。"""
    try:
        conn = _get_conn(database)
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE `{table}`")
        return f"表 `{database}`.`{table}` 已被截断。"
    except Exception as e:
        return f"截断失败：{e}"
    finally:
        conn.close()


@tool
def execute_dml(database: str, sql: str) -> str:
    """执行 DML 语句（INSERT, UPDATE, DELETE）。
    ⚠️ 危险操作：会修改数据，请确认后执行。"""
    sql_upper = sql.strip().upper()
    allowed_prefixes = ("INSERT", "UPDATE", "DELETE")
    if not any(sql_upper.startswith(p) for p in allowed_prefixes):
        return f"错误：该语句不是合法的 DML 语句。允许的操作：{allowed_prefixes}"
    try:
        conn = _get_conn(database)
        with conn.cursor() as cur:
            cur.execute(sql)
            affected = cur.rowcount
        return f"DML 执行成功，受影响行数：{affected}"
    except Exception as e:
        return f"DML 执行失败：{e}"
    finally:
        conn.close()


@tool
def purge_binlog(before_datetime: str) -> str:
    """清理指定时间之前的 binlog 文件。
    ⚠️ 高危操作：清理后无法用于基于时间点的恢复，请确认后执行。
    参数 before_datetime 格式：'YYYY-MM-DD HH:MM:SS'"""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(f"PURGE BINARY LOGS BEFORE '{before_datetime}'")
        return f"已清理 {before_datetime} 之前的 binlog 文件。"
    except Exception as e:
        return f"清理失败：{e}"
    finally:
        conn.close()


# 工具分组，供 agent.py 使用
SAFE_TOOLS = [
    query_database, show_databases, show_tables, describe_table,
    show_processlist, show_status, show_variables,
]

DANGEROUS_TOOLS = [
    execute_binlog_analysis, execute_ddl, truncate_table,
    execute_dml, purge_binlog,
]

ALL_TOOLS = SAFE_TOOLS + DANGEROUS_TOOLS
