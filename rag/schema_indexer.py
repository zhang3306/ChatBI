"""Index database table schemas into ChromaDB for RAG retrieval."""
import sys
from pathlib import Path
from itertools import count
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import MetaData, inspect
from config import SCHEMA_COLLECTION
from db.engine import get_engine
from rag.vector_store import VectorStore


def _table_schema_text(inspector, table_name: str) -> str:
    """Generate human-readable schema text for a table."""
    cols = inspector.get_columns(table_name)
    pk = inspector.get_pk_constraint(table_name)
    pk_cols = set(pk.get("constrained_columns", []))
    fks = inspector.get_foreign_keys(table_name)

    lines = [f"Table: {table_name}"]
    lines.append("Columns:")
    for c in cols:
        col_type = str(c["type"])
        nullable = "NULL" if c["nullable"] else "NOT NULL"
        is_pk = "PK" if c["name"] in pk_cols else ""
        default = f"default={c['default']}" if c["default"] else ""
        tags = ", ".join(filter(None, [is_pk, nullable, default]))
        lines.append(f"  - {c['name']} ({col_type}), {tags}")

    if fks:
        lines.append("Foreign Keys:")
        for fk in fks:
            for col_ref in fk.get("constrained_columns", []):
                ref_table = fk.get("referred_table", "?")
                ref_col = (fk.get("referred_columns") or ["?"])[0]
                lines.append(f"  - {table_name}.{col_ref} references {ref_table}.{ref_col}")

    return "\n".join(lines)


def _relationship_texts(inspector, table_name: str) -> list[dict]:
    """Extract FK relationship texts for a table."""
    fks = inspector.get_foreign_keys(table_name)
    results = []
    for fk in fks:
        for col_ref in fk.get("constrained_columns", []):
            ref_table = fk.get("referred_table", "?")
            ref_col = (fk.get("referred_columns") or ["?"])[0]
            results.append({
                "text": f"{table_name}.{col_ref} -> {ref_table}.{ref_col}",
                "metadata": {
                    "type": "relationship",
                    "from_table": table_name,
                    "from_column": col_ref,
                    "to_table": ref_table,
                    "to_column": ref_col,
                },
            })
    return results


def index_all_schemas(vs: VectorStore, force_reindex: bool = False):
    """Walk all user tables and index their schemas into ChromaDB."""
    if force_reindex:
        vs.delete_collection(SCHEMA_COLLECTION)

    engine = get_engine()
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    # Skip SQLite internal tables
    tables = [t for t in tables if not t.startswith("sqlite_") and not t.startswith("summary_")]

    ids, documents, metadatas = [], [], []
    rel_ids, rel_texts, rel_metadatas = [], [], []
    rid = count(1)
    rrid = count(1)

    for table in tables:
        schema_text = _table_schema_text(inspector, table)
        ids.append(f"schema:{table}")
        documents.append(schema_text)
        metadatas.append({"type": "table_schema", "table": table})

        for rel in _relationship_texts(inspector, table):
            rel_ids.append(f"rel:{table}:{next(rrid)}")
            rel_texts.append(rel["text"])
            rel_metadatas.append(rel["metadata"])

    if documents:
        vs.add_documents(SCHEMA_COLLECTION, ids, documents, metadatas)
    if rel_texts:
        vs.add_documents(SCHEMA_COLLECTION, rel_ids, rel_texts, rel_metadatas)

    return len(documents), len(rel_texts)
