"""SQL executor with summary table routing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sqlalchemy import text
from db.engine import get_engine
from db.summary_tables import route_to_summary
from sql.safety import validate, sanitize


class SQLExecutor:
    """Execute validated SQL queries with performance optimizations."""

    def __init__(self):
        self.engine = get_engine()

    def execute(self, sql: str, use_summary: bool = True) -> dict:
        """Execute SQL and return results.

        Args:
            sql: The SQL query to execute.
            use_summary: Whether to try routing to summary tables.

        Returns:
            {"data": DataFrame | None, "sql": str, "rows": int,
             "summary_routed": bool, "error": str | None}
        """
        # Validate
        safe, reason = validate(sql)
        if not safe:
            return {"data": None, "sql": sql, "rows": 0, "summary_routed": False, "error": reason}

        sql = sanitize(sql)
        original_sql = sql

        # Try summary table routing
        summary_sql = None
        if use_summary:
            summary_sql = route_to_summary(sql)
            if summary_sql:
                safe2, _ = validate(summary_sql)
                if safe2:
                    sql = summary_sql

        # Execute
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                col_names = list(result.keys())
                df = pd.DataFrame(rows, columns=col_names)
                return {
                    "data": df,
                    "sql": sql,
                    "rows": len(df),
                    "summary_routed": summary_sql is not None,
                    "error": None,
                }
        except Exception as e:
            return {
                "data": None,
                "sql": sql,
                "rows": 0,
                "summary_routed": False,
                "error": str(e),
            }

    def execute_raw(self, sql: str) -> pd.DataFrame | None:
        """Execute SQL directly without safety checks (for internal use only)."""
        try:
            return pd.read_sql(sql, self.engine)
        except Exception:
            return None
