"""Tool definitions for the LangChain ReAct Agent."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from langchain_core.tools import tool
from sql.generator import SQLGenerator
from sql.executor import SQLExecutor


# Shared state
_generator: SQLGenerator | None = None
_executor: SQLExecutor | None = None
_last_query_data: dict = {"data": None, "sql": ""}


def get_last_data():
    return _last_query_data["data"]


def get_last_sql():
    return _last_query_data["sql"]


@tool
def query_database(natural_language_query: str) -> str:
    """将自然语言问题转换为SQL并查询数据库，返回结果表格。
    当用户询问关于数据的问题时使用此工具。
    """
    if not _generator:
        return "系统未初始化：SQLGenerator 不可用"

    result = _generator.generate(natural_language_query)

    if not result["success"]:
        return f"无法为问题生成有效的SQL查询。请尝试换一种问法。"

    exec_result = _executor.execute(result["sql"]) if _executor else None

    if not exec_result or exec_result["error"]:
        error = exec_result["error"] if exec_result else "执行器未初始化"
        return f"查询执行失败：{error}"

    if exec_result["data"] is None or exec_result["data"].empty:
        return "查询执行成功，但没有匹配的数据。"

    df = exec_result["data"]
    summary = f"查询返回 {len(df)} 行结果。\n\n"
    summary += df.head(20).to_markdown(index=False, numalign="left")

    # Cache for visualization
    _last_query_data["data"] = df
    _last_query_data["sql"] = exec_result["sql"]

    return summary


@tool
def get_table_schema(table_name: str) -> str:
    """获取数据库中某张表的完整列定义。当用户询问表结构时使用。
    """
    if not _executor:
        return "系统未初始化"

    result = _executor.execute_raw(
        f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    if result is not None and not result.empty:
        return f"表 {table_name} 的结构：\n```\n{result.iloc[0, 0]}\n```"
    return f"未找到表：{table_name}"


@tool
def get_example_queries(topic: str) -> str:
    """获取某个主题的SQL查询示例。主题如：设备统计、语音分析、工单分析等。"""
    from rag.example_indexer import EXAMPLES

    matching = []
    for ex in EXAMPLES:
        if any(topic in t for t in ex["tags"]) or topic in ex["question"]:
            matching.append(ex)

    if not matching:
        return f"没有找到关于「{topic}」的示例。"

    lines = [f"找到 {len(matching)} 个相关示例：\n"]
    for ex in matching[:5]:
        lines.append(f"问题：{ex['question']}")
        lines.append(f"SQL：{ex['sql']}\n")
    return "\n".join(lines)


def init_tools(generator: SQLGenerator, executor: SQLExecutor):
    """Inject shared dependencies into tool modules."""
    global _generator, _executor
    _generator = generator
    _executor = executor
    _last_query_data["data"] = None
    _last_query_data["sql"] = ""
