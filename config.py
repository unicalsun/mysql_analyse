#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : config.py
@Author  : Evan Sun
@Date    : 2026-09-09
@Desc    : 环境变量配置加载
"""

import os
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

# 以下是使用 dict() 构造函数，所以MYSQL_CONFIG是一个字典类型，里面包含了MySQL的连接配置参数。敏感信息（如密码）从环境变量中读取，确保安全性。
# MySQL 配置 — 敏感信息统一从 .env 读取，不设 fallback
MYSQL_CONFIG = dict(
    host=os.environ["MYSQL_HOST"],
    port=int(os.environ["MYSQL_PORT"]),
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASSWORD"],
    database=os.environ.get("MYSQL_DATABASE", ""),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
)

# LLM 配置
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek:deepseek-v4-flash")
# langchain-deepseek 自动读取 DEEPSEEK_API_KEY 环境变量
# 若配置了 LLM_API_KEY 则作为 fallback 设置 DEEPSEEK_API_KEY
if os.getenv("LLM_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
    os.environ["DEEPSEEK_API_KEY"] = os.getenv("LLM_API_KEY")

