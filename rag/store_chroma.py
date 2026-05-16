"""ChromaDB-based vector store — semantic search with ONNX embeddings.

Requires:
    pip install chromadb

The ONNX model (~79MB) is auto-downloaded on first use from HuggingFace.
If download fails (network restrictions), callers should catch the exception
and fall back to rag.store_offline.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from config import CHROMA_PERSIST_DIR


class VectorStore:
    """ChromaDB vector store with persistent ONNX embeddings."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    def get_or_create_collection(self, name: str):
        return self.client.get_or_create_collection(name=name)

    def add_documents(self, collection_name: str, ids: list[str],
                      documents: list[str], metadatas: list[dict] | None = None):
        col = self.get_or_create_collection(collection_name)
        col.add(ids=ids, documents=documents, metadatas=metadatas or [{}] * len(ids))

    def query(self, collection_name: str, query_text: str,
              n_results: int = 5) -> dict:
        col = self.get_or_create_collection(collection_name)
        return col.query(query_texts=[query_text], n_results=n_results)

    def count(self, collection_name: str) -> int:
        col = self.get_or_create_collection(collection_name)
        return col.count()

    def peek(self, collection_name: str, limit: int = 5):
        col = self.get_or_create_collection(collection_name)
        return col.peek(limit)

    def delete_collection(self, name: str):
        try:
            self.client.delete_collection(name)
        except (ValueError, Exception):
            pass
