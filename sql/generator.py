"""Text2SQL generator — converts NL to SQL using RAG + LLM."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage
from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    DEEPSEEK_TEMPERATURE, MAX_RETRIES,
)
from prompts.templates import SQL_GENERATION
from rag.retriever import Retriever
from sql.safety import validate, sanitize


class SQLGenerator:
    """Generates SQL from natural language via RAG + LLM."""

    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.llm = None
        if DEEPSEEK_API_KEY:
            self.llm = ChatDeepSeek(
                model=DEEPSEEK_MODEL,
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL,
                temperature=DEEPSEEK_TEMPERATURE,
            )

    def generate(self, question: str, llm=None) -> dict:
        """Generate and validate SQL from a natural language question.

        Returns:
            {"sql": str, "context": dict, "attempts": int, "success": bool}
        """
        if llm:
            self.llm = llm

        context = self.retriever.retrieve(question)

        schemas_text = "\n\n".join(s["text"] for s in context["schemas"])
        relationships_text = "\n".join(r["text"] for r in context["relationships"])
        examples_text = "\n\n".join(e["text"] for e in context["examples"])

        prompt = SQL_GENERATION.format(
            schemas=schemas_text or "无相关表结构",
            relationships=relationships_text or "无关联关系",
            examples=examples_text or "无参考示例",
            question=question,
        )

        sql = ""
        attempts = 0
        success = False

        for attempt in range(MAX_RETRIES + 1):
            attempts += 1
            try:
                if self.llm:
                    response = self.llm.invoke([HumanMessage(content=prompt)])
                    sql = response.content.strip() if hasattr(response, 'content') else str(response)
                else:
                    sql = self._mock_generate(question)

                sql = self._extract_sql(sql)
            except Exception as e:
                if attempt < MAX_RETRIES:
                    prompt += f"\n\nPrevious attempt failed: {e}\nPlease retry.\nSQL:"
                continue

            # Validate
            safe, reason = validate(sql)
            if safe:
                sql = sanitize(sql)
                success = True
                break
            else:
                if attempt < MAX_RETRIES:
                    prompt += f"\n\nInvalid SQL: {reason}\nPlease correct.\nSQL:"

        return {
            "sql": sql,
            "context": context,
            "attempts": attempts,
            "success": success,
        }

    def _extract_sql(self, text: str) -> str:
        """Extract SQL from LLM response — handles markdown code fences."""
        text = text.strip()
        if "```" in text:
            # Find the SQL code block
            blocks = text.split("```")
            for i, block in enumerate(blocks):
                block = block.strip()
                if block.upper().startswith("SQL") or block.upper().startswith("SELECT"):
                    return block.removeprefix("SQL").removeprefix("sql").strip()
                if block.upper().startswith("SELECT"):
                    return block
            # Fallback: find any block containing SELECT
            for block in blocks:
                if "SELECT" in block.upper():
                    return block.strip()
        return text

    def _mock_generate(self, question: str) -> str:
        """Fallback when no API key is configured — returns a safe default."""
        return "SELECT COUNT(*) FROM devices LIMIT 100"
