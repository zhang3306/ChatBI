"""Initialize the RAG index — seed schemas and examples into ChromaDB.

Usage:
    python scripts/index.py
    python scripts/index.py --force    # reindex from scratch
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from rag.vector_store import VectorStore
from rag.schema_indexer import index_all_schemas
from rag.example_indexer import index_all_examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Reindex from scratch")
    args = parser.parse_args()

    vs = VectorStore()
    n_schemas, n_rels = index_all_schemas(vs, force_reindex=args.force)
    n_examples = index_all_examples(vs, force_reindex=args.force)
    print(f"[OK] Index done: {n_schemas} schemas, {n_rels} relations, {n_examples} SQL examples")


if __name__ == "__main__":
    main()
