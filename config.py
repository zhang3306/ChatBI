"""Centralized configuration — reads from env vars with sensible defaults."""
import os
from pathlib import Path

ROOT = Path(__file__).parent

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-253bbcd600bd4f5caeb6eea9505425fd")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_TEMPERATURE = 0.0

# SQLite
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(ROOT / "data" / "operations.db"))

# ChromaDB (used when available; falls back to offline keyword)
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(ROOT / "data" / "chroma_db"))

# Document store collections
SCHEMA_COLLECTION = "table_schemas"
EXAMPLE_COLLECTION = "sql_examples"

# Retrieval
TOP_K_SCHEMAS = 5
TOP_K_EXAMPLES = 3

# SQL safety
MAX_ROWS_DEFAULT = 100
SUMMARY_TABLE_THRESHOLD = 100_000

# Agent
MAX_HISTORY_TURNS = 10
MAX_RETRIES = 2

# Seed data
SEED_SCALE = float(os.getenv("SEED_SCALE", "0.01"))
