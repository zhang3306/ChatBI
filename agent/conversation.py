"""Multi-turn conversational ChatBI — manual Agent loop (no langchain Agent dependency)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    DEEPSEEK_TEMPERATURE, MAX_HISTORY_TURNS,
)
from sql.generator import SQLGenerator
from sql.executor import SQLExecutor
from agent.tools import query_database, get_table_schema, get_example_queries, init_tools


class ConversationAgent:
    """Simple multi-turn agent with manual tool calling loop."""

    def __init__(self, generator: SQLGenerator, executor: SQLExecutor):
        self.generator = generator
        self.executor = executor
        init_tools(generator, executor)
        self.history: list[dict] = []
        self.llm = None
        if DEEPSEEK_API_KEY:
            self.llm = ChatDeepSeek(
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=DEEPSEEK_TEMPERATURE,
            )

    def chat(self, message: str) -> dict:
        """Process a message, run SQL query, return results."""
        self.history.append({"role": "user", "message": message})
        # Keep only last N turns
        if len(self.history) > MAX_HISTORY_TURNS * 2:
            self.history = self.history[-MAX_HISTORY_TURNS * 2:]

        if not self.llm:
            return {
                "response": "请先配置 DEEPSEEK_API_KEY 环境变量再使用。",
                "data": None, "sql": None,
            }

        try:
            # 1. Inject context from conversation history
            if len(self.history) > 1:
                context_prompt = self._build_context_prompt(message)
                response = self.llm.invoke([HumanMessage(content=context_prompt)])
                decision = response.content.strip() if hasattr(response, 'content') else str(response)
            else:
                decision = "query"

            # 2. Generate SQL
            result = self.generator.generate(message, llm=self.llm)

            if not result["success"]:
                reply = f"无法为这个问题生成有效的SQL查询。请换个问法。"
                self.history.append({"role": "assistant", "message": reply})
                return {"response": reply, "data": None, "sql": None, "success": False}

            # 3. Execute SQL
            exec_result = self.executor.execute(result["sql"])

            if exec_result["error"]:
                reply = f"查询执行失败：{exec_result['error']}"
                self.history.append({"role": "assistant", "message": reply})
                return {"response": reply, "data": None, "sql": result["sql"], "success": False}

            df = exec_result["data"]
            if df is None or df.empty:
                reply = "查询执行成功，但没有匹配的数据。"
                self.history.append({"role": "assistant", "message": reply})
                return {"response": reply, "data": df, "sql": result["sql"], "success": True}

            # 4. Format response
            row_count = len(df)
            preview = df.head(5).to_markdown(index=False, numalign="left")
            format_prompt = (
                f"用户问题：{message}\n"
                f"查询结果（前5行）：\n{preview}\n"
                f"总行数：{row_count}\n\n"
                f"请用自然语言简要总结查询结果，语气友好干练，不超过3句话。\n总结："
            )
            fmt_resp = self.llm.invoke([HumanMessage(content=format_prompt)])
            reply = fmt_resp.content.strip() if hasattr(fmt_resp, 'content') else str(fmt_resp)

            # Store for visualization
            from agent.tools import _last_query_data
            _last_query_data["data"] = df
            _last_query_data["sql"] = result["sql"]

            self.history.append({"role": "assistant", "message": reply})
            return {"response": reply, "data": df, "sql": result["sql"], "success": True}

        except Exception as e:
            reply = f"处理出错：{str(e)}"
            return {"response": reply, "data": None, "sql": None, "success": False}

    def _build_context_prompt(self, question: str) -> str:
        """Check if question is a follow-up referencing previous context."""
        recent = self.history[-4:-1] if len(self.history) > 4 else self.history[:-1]
        context = "\n".join(
            f"{'用户' if m['role']=='user' else '系统'}: {m['message']}"
            for m in recent[-3:]
        )
        return (
            f"以下是对话上下文：\n{context}\n\n"
            f"用户新问题：{question}\n\n"
            f"如果这是追问（如'上海呢？'、'按类型拆分'），回答 'query' 继续查询。\n"
            f"如果与数据无关（问候、闲聊），直接回答用户。\n"
            f"你的回复："
        )

    def clear_memory(self):
        self.history = []
        from agent.tools import _last_query_data
        _last_query_data["data"] = None
        _last_query_data["sql"] = ""
