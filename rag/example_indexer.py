"""Index canonical SQL query examples into ChromaDB."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import EXAMPLE_COLLECTION
from rag.vector_store import VectorStore


# 40+ canonical query examples covering common operations scenarios
EXAMPLES = [
    # ── Device counts & status ──
    {"question": "有多少在线设备？", "sql": "SELECT COUNT(*) FROM devices WHERE status = 'online'", "tags": ["count", "devices", "status"]},
    {"question": "有多少离线设备？", "sql": "SELECT COUNT(*) FROM devices WHERE status = 'offline'", "tags": ["count", "devices", "status"]},
    {"question": "报错设备有多少？", "sql": "SELECT COUNT(*) FROM devices WHERE status = 'error'", "tags": ["count", "devices", "error"]},
    {"question": "各状态的设备数量分布", "sql": "SELECT status, COUNT(*) AS count FROM devices GROUP BY status", "tags": ["count", "devices", "group"]},

    # ── Region-based queries ──
    {"question": "北京的在线设备数", "sql": "SELECT COUNT(*) FROM devices d JOIN regions r ON d.region_id = r.id WHERE r.city = '北京' AND d.status = 'online'", "tags": ["join", "count", "region", "devices"]},
    {"question": "各城市设备数量排名", "sql": "SELECT r.province, r.city, COUNT(d.id) AS device_count FROM regions r JOIN devices d ON d.region_id = r.id GROUP BY r.province, r.city ORDER BY device_count DESC LIMIT 10", "tags": ["join", "aggregation", "ranking"]},
    {"question": "安徽省设备总量", "sql": "SELECT COUNT(*) FROM devices d JOIN regions r ON d.region_id = r.id WHERE r.province = '安徽'", "tags": ["join", "count", "province"]},
    {"question": "设备量前三的城市", "sql": "SELECT r.city, COUNT(d.id) AS cnt FROM regions r JOIN devices d ON d.region_id = r.id GROUP BY r.city ORDER BY cnt DESC LIMIT 3", "tags": ["join", "ranking", "top"]},

    # ── Device type breakdown ──
    {"question": "各类设备的数量分布", "sql": "SELECT dt.type_name, COUNT(d.id) AS count FROM device_types dt LEFT JOIN devices d ON d.device_type_id = dt.id GROUP BY dt.type_name ORDER BY count DESC", "tags": ["join", "group", "device_type"]},
    {"question": "安防类设备有多少", "sql": "SELECT COUNT(*) FROM devices d JOIN device_types dt ON d.device_type_id = dt.id WHERE dt.category = '安防'", "tags": ["join", "category", "count"]},
    {"question": "在线率最高的设备类型", "sql": "SELECT dt.type_name, ROUND(SUM(CASE WHEN d.status='online' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS online_rate FROM device_types dt JOIN devices d ON d.device_type_id = dt.id GROUP BY dt.type_name ORDER BY online_rate DESC LIMIT 5", "tags": ["join", "rate", "ranking"]},

    # ── Event analytics ──
    {"question": "今天的报警事件数", "sql": "SELECT COUNT(*) FROM device_events WHERE DATE(occurred_at) = DATE('now') AND event_type = 'alert'", "tags": ["count", "events", "today"]},
    {"question": "各事件类型数量", "sql": "SELECT event_type, COUNT(*) AS count FROM device_events GROUP BY event_type ORDER BY count DESC", "tags": ["events", "group"]},
    {"question": "最近7天每日事件趋势", "sql": "SELECT DATE(occurred_at) AS day, COUNT(*) AS count FROM device_events WHERE occurred_at >= DATE('now', '-7 days') GROUP BY DATE(occurred_at) ORDER BY day", "tags": ["events", "trend", "7days"]},
    {"question": "一个月内的错误事件总数", "sql": "SELECT COUNT(*) FROM device_events WHERE event_type = 'error' AND occurred_at >= DATE('now', '-30 days')", "tags": ["events", "error", "month"]},

    # ── Voice command analysis ──
    {"question": "每天语音命令量", "sql": "SELECT DATE(created_at) AS day, COUNT(*) AS count FROM voice_commands GROUP BY DATE(created_at) ORDER BY day DESC LIMIT 7", "tags": ["voice", "daily", "trend"]},
    {"question": "最常用的语音意图TOP10", "sql": "SELECT intent, COUNT(*) AS count FROM voice_commands GROUP BY intent ORDER BY count DESC LIMIT 10", "tags": ["voice", "intent", "ranking"]},
    {"question": "控制设备类的语音命令数量", "sql": "SELECT COUNT(*) FROM voice_commands WHERE intent = 'control_device'", "tags": ["voice", "intent", "count"]},
    {"question": "广东的语音命令数量", "sql": "SELECT COUNT(*) FROM voice_commands vc JOIN devices d ON vc.device_id = d.id JOIN regions r ON d.region_id = r.id WHERE r.province = '广东'", "tags": ["voice", "join", "province"]},

    # ── Service orders ──
    {"question": "待处理工单数量", "sql": "SELECT COUNT(*) FROM service_orders WHERE status = 'pending'", "tags": ["order", "pending", "count"]},
    {"question": "本月新增工单数", "sql": "SELECT COUNT(*) FROM service_orders WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')", "tags": ["order", "month", "count"]},
    {"question": "各类型工单数量", "sql": "SELECT order_type, COUNT(*) AS count FROM service_orders GROUP BY order_type ORDER BY count DESC", "tags": ["order", "group"]},
    {"question": "紧急工单有多少", "sql": "SELECT COUNT(*) FROM service_orders WHERE priority = 'urgent' AND status != 'done'", "tags": ["order", "urgent", "count"]},
    {"question": "本月已完成工单的平均处理时间", "sql": "SELECT AVG(CAST((julianday(resolved_at) - julianday(created_at)) * 24 AS INTEGER)) AS avg_hours FROM service_orders WHERE status = 'done' AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')", "tags": ["order", "avg", "processing_time"]},

    # ── User analytics ──
    {"question": "总用户数", "sql": "SELECT COUNT(*) FROM users", "tags": ["user", "count"]},
    {"question": "活跃用户数", "sql": "SELECT COUNT(*) FROM users WHERE status = 'active'", "tags": ["user", "active", "count"]},
    {"question": "各地区用户数", "sql": "SELECT r.province, r.city, COUNT(DISTINCT u.id) AS user_count FROM regions r LEFT JOIN devices d ON d.region_id = r.id LEFT JOIN users u ON u.id = d.user_id GROUP BY r.province, r.city ORDER BY user_count DESC LIMIT 10", "tags": ["user", "region", "join"]},
    {"question": "新增用户趋势（最近7天）", "sql": "SELECT DATE(registered_at) AS day, COUNT(*) AS new_users FROM users WHERE registered_at >= DATE('now', '-7 days') GROUP BY DATE(registered_at) ORDER BY day", "tags": ["user", "trend", "new"]},

    # ── Complex queries ──
    {"question": "各城市设备类型分布", "sql": "SELECT r.city, dt.category, COUNT(d.id) AS cnt FROM regions r JOIN devices d ON d.region_id = r.id JOIN device_types dt ON d.device_type_id = dt.id GROUP BY r.city, dt.category ORDER BY r.city, cnt DESC", "tags": ["join", "multi", "breakdown"]},
    {"question": "报警最多的设备TOP20", "sql": "SELECT d.device_name, COUNT(e.id) AS alert_count FROM devices d JOIN device_events e ON e.device_id = d.id WHERE e.event_type = 'alert' GROUP BY d.id ORDER BY alert_count DESC LIMIT 20", "tags": ["join", "ranking", "events"]},
    {"question": "超过3天未处理的工单", "sql": "SELECT * FROM service_orders WHERE status = 'pending' AND created_at < DATE('now', '-3 days') ORDER BY created_at ASC LIMIT 100", "tags": ["order", "overdue"]},
    {"question": "按设备类型统计报错率", "sql": "SELECT dt.type_name, SUM(CASE WHEN d.status='error' THEN 1 ELSE 0 END) * 100.0 / COUNT(d.id) AS error_rate FROM device_types dt JOIN devices d ON d.device_type_id = dt.id GROUP BY dt.type_name ORDER BY error_rate DESC", "tags": ["join", "rate", "error"]},

    # ── Time-series ──
    {"question": "上月每天的活跃设备数", "sql": "SELECT DATE(d.updated_at) AS day, COUNT(DISTINCT d.id) AS active_devices FROM devices d WHERE d.status = 'online' AND d.updated_at >= DATE('now', '-1 month') GROUP BY day ORDER BY day", "tags": ["time", "daily", "trend"]},
    {"question": "上周末的最热门语音意图", "sql": "SELECT vc.intent, COUNT(*) AS cnt FROM voice_commands vc WHERE vc.created_at BETWEEN DATE('now', '-8 days') AND DATE('now', '-1 days') GROUP BY vc.intent ORDER BY cnt DESC", "tags": ["voice", "weekend", "ranking"]},

    # ── Comprehensive BI ──
    {"question": "各省设备在线率", "sql": "SELECT r.province, COUNT(d.id) AS total, SUM(CASE WHEN d.status='online' THEN 1 ELSE 0 END) AS online, ROUND(SUM(CASE WHEN d.status='online' THEN 1 ELSE 0 END) * 100.0 / COUNT(d.id), 1) AS online_rate FROM regions r JOIN devices d ON d.region_id = r.id GROUP BY r.province", "tags": ["bi", "province", "rate"]},
    {"question": "设备总量、在线量、报错量概览", "sql": "SELECT COUNT(*) AS total, SUM(CASE WHEN status='online' THEN 1 ELSE 0 END) AS online, SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS error_count FROM devices", "tags": ["bi", "overview"]},
    {"question": "用户拥有设备数分布", "sql": "SELECT device_count, COUNT(*) AS user_count FROM (SELECT user_id, COUNT(*) AS device_count FROM devices GROUP BY user_id) GROUP BY device_count ORDER BY device_count LIMIT 20", "tags": ["bi", "distribution"]},
    {"question": "工单处理效率趋势", "sql": "SELECT DATE(created_at) AS day, AVG(CAST((julianday(resolved_at) - julianday(created_at)) * 24 AS INTEGER)) AS avg_resolve_hours FROM service_orders WHERE status='done' AND resolved_at IS NOT NULL GROUP BY day ORDER BY day DESC LIMIT 30", "tags": ["bi", "trend", "efficiency"]},
]


def index_all_examples(vs: VectorStore, force_reindex: bool = False):
    """Index all canonical SQL examples into ChromaDB."""
    if force_reindex:
        vs.delete_collection(EXAMPLE_COLLECTION)

    ids = [f"example:{i}" for i in range(len(EXAMPLES))]
    documents = [f"Question: {e['question']}\nSQL: {e['sql']}" for e in EXAMPLES]
    metadatas = [{"type": "sql_example", "tags": " ".join(e["tags"]), "question": e["question"]} for e in EXAMPLES]

    vs.add_documents(EXAMPLE_COLLECTION, ids, documents, metadatas)
    return len(ids)
