"""SQL safety validator."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlparse
from config import MAX_ROWS_DEFAULT


FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE",
                       "ALTER", "CREATE", "TRUNCATE", "REPLACE",
                       "EXEC", "EXECUTE", "ATTACH", "DETACH",
                       "REINDEX", "RELEASE", "SAVEPOINT"}

DANGEROUS_FUNCTIONS = {"load_extension", "readfile", "writefile"}


def validate(sql: str) -> tuple[bool, str]:
    """Validate that SQL is read-only and safe to execute.

    Returns:
        (is_safe: bool, reason: str)
    """
    sql = sql.strip().rstrip(";").strip()

    if not sql:
        return False, "Empty SQL"

    # Parse into statements
    try:
        statements = sqlparse.parse(sql)
    except Exception as e:
        return False, f"Parse error: {e}"

    if not statements:
        return False, "No valid SQL statement"

    # Check single statement
    raw = sqlparse.split(sql)
    if len(raw) > 1:
        return False, f"Multiple statements detected ({len(raw)}), only single SELECT allowed"

    stmt = statements[0]

    # Check statement type
    stmt_type = stmt.get_type().upper()
    if stmt_type != "SELECT":
        return False, f"Only SELECT allowed, got: {stmt_type}"

    # Check for forbidden keywords in token content
    tokens_str = " ".join(t.value.upper() for t in stmt.flatten() if t.ttype is sqlparse.tokens.Keyword)
    for kw in FORBIDDEN_KEYWORDS:
        if kw in tokens_str.split():
            return False, f"Forbidden keyword: {kw}"

    # Check for dangerous functions
    for token in stmt.flatten():
        if token.ttype is sqlparse.tokens.Name.Builtin:
            if token.value.lower() in DANGEROUS_FUNCTIONS:
                return False, f"Dangerous function: {token.value}"

    return True, ""


def sanitize(sql: str) -> str:
    """Defense-in-depth: append LIMIT if not present."""
    s = sql.strip().rstrip(";").strip()
    if s.upper().lstrip().startswith("SELECT") and "LIMIT" not in s.upper():
        s += f" LIMIT {MAX_ROWS_DEFAULT}"
    return s
