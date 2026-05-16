"""Pre-built summary table definitions and query routing.

Optimizes common aggregation queries by maintaining pre-computed summary tables,
so simple COUNT/GROUP BY queries don't scan millions of raw rows.

Key design:
- summary tables created as regular SQLite tables with triggers for refresh
- SQL executor inspects incoming query and rewrites to summary table if applicable
"""
import re
from sqlalchemy import text
from .engine import get_engine

# ── DDL ────────────────────────────────────────────────────────────

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS summary_daily_events AS
    SELECT device_id, DATE(occurred_at) AS event_date, event_type, COUNT(*) AS event_count
    FROM device_events
    GROUP BY device_id, DATE(occurred_at), event_type
    """,
    """
    CREATE TABLE IF NOT EXISTS summary_daily_voice AS
    SELECT device_id, DATE(created_at) AS cmd_date, intent, COUNT(*) AS cmd_count
    FROM voice_commands
    GROUP BY device_id, DATE(created_at), intent
    """,
    """
    CREATE TABLE IF NOT EXISTS summary_device_stats AS
    SELECT dt.id AS device_type_id, dt.type_name, dt.category,
           COUNT(d.id) AS total_devices,
           SUM(CASE WHEN d.status = 'online' THEN 1 ELSE 0 END) AS online_devices,
           SUM(CASE WHEN d.status = 'error' THEN 1 ELSE 0 END) AS error_devices
    FROM device_types dt
    LEFT JOIN devices d ON d.device_type_id = dt.id
    GROUP BY dt.id
    """,
    """
    CREATE TABLE IF NOT EXISTS summary_region_stats AS
    SELECT r.province, r.city,
           COUNT(DISTINCT d.id) AS device_count,
           COUNT(DISTINCT d.user_id) AS user_count,
           SUM(CASE WHEN d.status = 'error' THEN 1 ELSE 0 END) AS error_device_count
    FROM regions r
    LEFT JOIN devices d ON d.region_id = r.id
    GROUP BY r.province, r.city
    """,
    """
    CREATE TABLE IF NOT EXISTS summary_weekly_service_orders AS
    SELECT DATE(created_at, 'weekday 0') AS week_start,
           order_type, status,
           COUNT(*) AS order_count
    FROM service_orders
    GROUP BY DATE(created_at, 'weekday 0'), order_type, status
    """,
]


def create_summary_tables():
    """Create or refresh all summary tables."""
    engine = get_engine()
    with engine.connect() as conn:
        for ddl in DDL_STATEMENTS:
            table_name = _extract_table_name(ddl)
            # drop if exists to refresh
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            conn.execute(text(ddl))
        conn.commit()


def _extract_table_name(ddl: str) -> str:
    m = re.search(r"CREATE TABLE IF NOT EXISTS (\w+)", ddl)
    return m.group(1) if m else "unknown"


# ── Query routing patterns ──────────────────────────────────────────
# Pattern -> (summary_table, rewrite_template)
ROUTING_RULES = [
    # SELECT COUNT(*) FROM devices WHERE status = 'X'
    (r"SELECT\s+COUNT\(\*\)\s+FROM\s+devices\s+WHERE\s+status\s*=\s*'(\w+)'",
     "SELECT online_devices FROM summary_device_stats WHERE type_name LIKE '%' LIMIT 1",
     False),

    # SELECT COUNT(*) FROM devices (simple count)
    (r"SELECT\s+COUNT\(\*\)\s+FROM\s+devices\s*$",
     "SELECT SUM(total_devices) FROM summary_device_stats",
     False),

    # SELECT COUNT(*) FROM devices WHERE device_type_id = N
    (r"SELECT\s+COUNT\(\*\)\s+FROM\s+devices\s+WHERE\s+device_type_id\s*=\s*(\d+)",
     "SELECT SUM(total_devices) FROM summary_device_stats WHERE device_type_id = {0}",
     True),

    # COUNT from device_events grouped by date (analytics pattern)
    (r"SELECT\s+COUNT\(\*\)\s+FROM\s+device_events\s+WHERE\s+occurred_at\s+BETWEEN",
     "SELECT SUM(event_count) FROM summary_daily_events WHERE event_date BETWEEN",
     True),
]


def route_to_summary(sql: str) -> str | None:
    """Check if SQL matches a known pattern and can be routed to a summary table.

    Returns the rewritten SQL, or None if no routing applies.
    """
    sql_clean = sql.strip().rstrip(";").strip()
    for pattern, template, param_match in ROUTING_RULES:
        m = re.match(pattern, sql_clean, re.IGNORECASE)
        if m:
            if param_match and m.groups():
                return template.replace("{0}", m.group(1))
            return template
    return None
