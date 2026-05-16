"""Batch mock data generator for the smart home operations database.

Usage:
    python -m chatbi.db.seed --scale 1.0    # full ~4.6M rows
    python -m chatbi.db.seed --scale 0.1    # ~460K rows (quick demo)
    python -m chatbi.db.seed --scale 0.01   # ~46K rows (dev test)
"""
import random
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text

# Allow running as python -m db.seed from chatbi/ directory
import sys
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from db.engine import init_db, get_engine
    from db.models import Base
else:
    from .engine import init_db, get_engine
    from .models import Base


# ── seed configuration ──────────────────────────────────────────────
PROVINCES = ["安徽", "广东", "新疆", "山东", "江苏", "浙江", "福建", "湖南", "四川", "湖北"]
CITIES = {
    "安徽": ["合肥", "芜湖", "蚌埠", "阜阳", "六安"],
    "广东": ["广州", "深圳", "东莞", "佛山", "珠海"],
    "新疆": ["乌鲁木齐", "克拉玛依", "昌吉", "伊犁", "阿克苏"],
    "山东": ["济南", "青岛", "烟台", "潍坊", "临沂"],
    "江苏": ["南京", "苏州", "无锡", "常州", "南通"],
    "浙江": ["杭州", "宁波", "温州", "嘉兴", "绍兴"],
    "福建": ["福州", "厦门", "泉州", "漳州", "莆田"],
    "湖南": ["长沙", "株洲", "湘潭", "衡阳", "岳阳"],
    "四川": ["成都", "绵阳", "德阳", "宜宾", "南充"],
    "湖北": ["武汉", "宜昌", "襄阳", "荆州", "黄石"],
}
DEVICE_TYPES = [
    ("智能灯", "照明"), ("智能门锁", "安防"), ("智能恒温器", "舒适"),
    ("智能摄像头", "安防"), ("智能音箱", "娱乐"), ("智能窗帘", "舒适"),
    ("智能插座", "家电"), ("空气净化器", "舒适"), ("智能电视", "娱乐"),
    ("智能电饭煲", "家电"), ("智能洗衣机", "家电"), ("扫地机器人", "家电"),
    ("智能门铃", "安防"), ("智能烟感", "安防"), ("智能体脂秤", "健康"),
    ("智能灯带", "照明"), ("智能投影仪", "娱乐"), ("智能晾衣架", "家电"),
    ("智能宠物喂食器", "宠物"), ("智能加湿器", "舒适"),
    ("净水器", "家电"), ("智能热水器", "家电"), ("智能床垫", "健康"),
    ("智能窗帘电机", "舒适"), ("智能空调伴侣", "舒适"), ("智能网关", "网络"),
]
DEVICE_STATUSES = ["online", "online", "online", "online", "offline", "offline", "error"]
EVENT_TYPES = ["power_on", "power_off", "alert", "fw_update", "error", "heartbeat"]
VOICE_INTENTS = [
    "search_movie", "query_weather", "control_device", "chat", "play_music",
    "set_timer", "query_news", "call_contact", "check_health", "order_food",
]
ORDER_TYPES = ["repair", "install", "maintain", "complaint"]
ORDER_PRIORITIES = ["low", "normal", "normal", "normal", "high", "urgent"]
ORDER_STATUSES = ["pending", "pending", "processing", "done", "done", "done", "cancelled"]


def _random_date(start: datetime, end: datetime) -> datetime:
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))


def seed(scale: float = 1.0, verbose: bool = True):
    """Generate mock data at the given scale factor.  1.0 ≈ 4.6M rows."""
    t0 = time.time()

    if verbose:
        print(f"[seed] scale={scale}, target ~{int(4.6 * scale)}M rows")
        print()

    engine = init_db()
    conn = engine.connect()
    # basic optimizations
    conn.execute(text("PRAGMA synchronous = OFF"))
    conn.execute(text("PRAGMA journal_mode = MEMORY"))
    conn.execute(text("PRAGMA cache_size = -80000"))
    conn.commit()

    # ── regions (fixed, ~3000 rows) ──────────────────────────
    n_districts = int(3000 * min(scale, 1.0))
    if verbose:
        print(f"[seed] generating {n_districts} regions...")
    region_rows = []
    districts_per_city = max(1, n_districts // (sum(len(c) for c in CITIES.values())))
    for province, cities in CITIES.items():
        for city in cities:
            for d in range(districts_per_city):
                region_rows.append({
                    "province": province,
                    "city": city,
                    "district": f"{city}区_{d}" if d < 10 else f"{city}{'县' if d % 2 else '市'}{d}",
                })
    _batch_insert(conn, "regions", region_rows)
    del region_rows

    # ── device_types (fixed, 26 rows) ────────────────────────
    if verbose:
        print(f"[seed] generating {len(DEVICE_TYPES)} device types...")
    dt_rows = [{"type_name": t, "category": c} for t, c in DEVICE_TYPES]
    _batch_insert(conn, "device_types", dt_rows)

    # fetch IDs
    region_ids = [r[0] for r in conn.execute(text("SELECT id FROM regions")).fetchall()]
    n_regions = len(region_ids)
    dt_ids = [r[0] for r in conn.execute(text("SELECT id FROM device_types")).fetchall()]
    n_dt = len(dt_ids)

    # ── users (scale * 1M) ───────────────────────────────────
    n_users = int(1_000_000 * scale)
    if verbose:
        print(f"[seed] generating {n_users} users...")
    user_rows = []
    phone_base = 13800000000
    for i in range(1, n_users + 1):
        user_rows.append({
            "name": f"用户{i}",
            "phone": str(phone_base + i),
            "registered_at": _random_date(datetime(2020, 1, 1), datetime(2025, 6, 1)),
            "status": random.choices(["active", "active", "active", "inactive", "deleted"], weights=[60, 20, 10, 7, 3])[0],
        })
    _batch_insert(conn, "users", user_rows)
    user_ids = [r[0] for r in conn.execute(text("SELECT id FROM users")).fetchall()]
    n_users_actual = len(user_ids)
    del user_rows

    # ── devices (scale * 5M) ─────────────────────────────────
    n_devices = int(5_000_000 * scale)
    if verbose:
        print(f"[seed] generating {n_devices} devices...")
    device_rows = []
    fw_versions = ["v2.1.0", "v2.1.1", "v2.2.0", "v3.0.0", "v3.0.1"]
    for i in range(1, n_devices + 1):
        device_rows.append({
            "device_name": f"{random.choice(DEVICE_TYPES)[0]}_{i}",
            "device_type_id": random.choice(dt_ids),
            "user_id": random.choice(user_ids),
            "region_id": random.choice(region_ids),
            "status": random.choice(DEVICE_STATUSES),
            "firmware_version": random.choice(fw_versions),
            "created_at": _random_date(datetime(2021, 1, 1), datetime(2025, 6, 1)),
        })
    _batch_insert(conn, "devices", device_rows)
    device_ids = [r[0] for r in conn.execute(text("SELECT id FROM devices")).fetchall()]
    n_devices_actual = len(device_ids)
    del device_rows

    # ── device_events (scale * 30M) ──────────────────────────
    n_events = int(30_000_000 * scale)
    if verbose:
        print(f"[seed] generating {n_events} device_events...")
    event_batch = []
    for i in range(1, n_events + 1):
        event_batch.append({
            "device_id": random.choice(device_ids),
            "event_type": random.choice(EVENT_TYPES),
            "event_detail": f"事件_{i}",
            "occurred_at": _random_date(datetime(2022, 1, 1), datetime(2025, 6, 1)),
        })
    _batch_insert(conn, "device_events", event_batch)
    del event_batch

    # ── voice_commands (scale * 10M) ─────────────────────────
    n_voice = int(10_000_000 * scale)
    if verbose:
        print(f"[seed] generating {n_voice} voice_commands...")
    voice_batch = []
    for i in range(1, n_voice + 1):
        voice_batch.append({
            "device_id": random.choice(device_ids),
            "command_text": f"语音命令_{i}",
            "intent": random.choice(VOICE_INTENTS),
            "response_text": f"响应_{i}",
            "created_at": _random_date(datetime(2022, 6, 1), datetime(2025, 6, 1)),
        })
    _batch_insert(conn, "voice_commands", voice_batch)
    del voice_batch

    # ── service_orders (scale * 500K) ────────────────────────
    n_orders = int(500_000 * scale)
    if verbose:
        print(f"[seed] generating {n_orders} service_orders...")
    order_batch = []
    for i in range(1, n_orders + 1):
        created = _random_date(datetime(2022, 1, 1), datetime(2025, 6, 1))
        resolved = None
        status = random.choice(ORDER_STATUSES)
        if status == "done":
            resolved = created + timedelta(hours=random.randint(1, 72))
        order_batch.append({
            "device_id": random.choice(device_ids),
            "order_type": random.choice(ORDER_TYPES),
            "priority": random.choice(ORDER_PRIORITIES),
            "status": status,
            "description": f"工单_{i}",
            "created_at": created,
            "resolved_at": resolved,
        })
    _batch_insert(conn, "service_orders", order_batch)
    del order_batch

    # cleanup
    conn.execute(text("PRAGMA synchronous = FULL"))
    conn.execute(text("PRAGMA journal_mode = DELETE"))
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    if verbose:
        totals = [(tn, 0) for tn in ["regions", "device_types", "users", "devices",
                                       "device_events", "voice_commands", "service_orders"]]
        engine2 = get_engine()
        c2 = engine2.connect()
        for tn, _ in totals:
            cnt = c2.execute(text(f"SELECT COUNT(*) FROM {tn}")).scalar()
            print(f"  {tn}: {cnt:,}")
        c2.close()
        print(f"[seed] done in {elapsed:.1f}s")


def _batch_insert(conn, table: str, rows: list, batch_size: int = 100_000):
    """Insert rows in batches using raw SQL for speed."""
    if not rows:
        return
    col_names = list(rows[0].keys())
    cols = ", ".join(col_names)
    placeholders = ", ".join([f":{c}" for c in col_names])
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        conn.execute(text(sql), batch)
    conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=0.01, help="Data scale factor (1.0 ≈ 4.6M rows)")
    args = parser.parse_args()
    seed(scale=args.scale)
