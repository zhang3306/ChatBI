"""Offline keyword-matching document store — saves/loads index from JSON."""
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "doc_store.json"


class DocumentStore:
    """Keyword-matching document store with JSON persistence."""

    def __init__(self):
        self._collections: dict[str, list[dict]] = {}
        self._keyword_index: dict[str, dict[str, list[int]]] = {}
        self._load()

    def save(self):
        """Persist collections to JSON."""
        data = {
            "collections": self._collections,
            "keyword_index": {k: dict(v) for k, v in self._keyword_index.items()},
        }
        _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load(self):
        """Load persisted collections from JSON."""
        if _STORE_PATH.exists():
            try:
                with open(_STORE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._collections = data.get("collections", {})
                idx = data.get("keyword_index", {})
                self._keyword_index = {
                    k: defaultdict(list, v) for k, v in idx.items()
                }
            except (json.JSONDecodeError, KeyError):
                pass

    def _get_stopwords(self) -> set[str]:
        return {"的", "了", "是", "在", "有", "和", "就", "不", "人", "都", "一",
                "个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
                "没有", "看", "好", "自己", "这", "the", "a", "an", "of", "in",
                "to", "is", "for", "on", "and", "or", "at", "by", "with", "from",
                "as", "into", "about", "after", "before", "between", "through",
                "during", "how", "what", "which", "who", "where", "when", "why"}

    def create_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = []
            self._keyword_index[name] = defaultdict(list)

    def get_collection(self, name: str) -> list[dict] | None:
        return self._collections.get(name)

    def add_documents(self, collection_name: str, ids: list[str],
                      documents: list[str], metadatas: list[dict] | None = None):
        col = self._collections.setdefault(collection_name, [])
        idx = self._keyword_index.setdefault(collection_name, defaultdict(list))

        for i, (doc_id, doc_text) in enumerate(zip(ids, documents)):
            entry = {"id": doc_id, "text": doc_text, "metadata": metadatas[i] if metadatas else {}}
            col.append(entry)

            # Index keywords (Chinese + English tokens)
            tokens = self._tokenize(doc_text)
            for token in set(tokens):
                if token not in self._get_stopwords() and len(token) >= 2:
                    idx[token].append(len(col) - 1)

        self.save()

    def query(self, collection_name: str, query_text: str, n_results: int = 5) -> dict:
        """Query by keyword matching, return most relevant documents."""
        col = self._collections.get(collection_name, [])
        if not col:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        tokens = self._tokenize(query_text)
        idx = self._keyword_index.get(collection_name, {})

        # Score each document by keyword overlap
        scores = defaultdict(int)
        for token in set(tokens):
            if token in self._get_stopwords() or len(token) < 2:
                continue
            for doc_pos in idx.get(token, []):
                scores[doc_pos] += 1

        # Sort by score (descending)
        ranked = sorted(scores.items(), key=lambda x: -x[1])

        if not ranked:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        top = ranked[:n_results]
        result_ids = [col[pos]["id"] for pos, _ in top]
        result_docs = [col[pos]["text"] for pos, _ in top]
        result_metas = [col[pos]["metadata"] for pos, _ in top]
        # Convert score to pseudo-distance (lower = better match)
        max_score = max(s for _, s in top) if top else 1
        result_dist = [1.0 - (s / max_score) for _, s in top]

        return {
            "ids": [result_ids],
            "documents": [result_docs],
            "metadatas": [result_metas],
            "distances": [result_dist],
        }

    def count(self, collection_name: str) -> int:
        return len(self._collections.get(collection_name, []))

    def peek(self, collection_name: str, limit: int = 5):
        col = self._collections.get(collection_name, [])
        return col[:limit]

    def delete_collection(self, name: str):
        self._collections.pop(name, None)
        self._keyword_index.pop(name, None)

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenizer — splits on whitespace/punctuation and extracts
        Chinese character bigrams (surrogate for word segmentation)."""
        import re
        # English/Latin tokens
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{1,}", text.lower())
        # Chinese bigrams
        chinese_chars = re.findall(r"[一-鿿]+", text)
        for chunk in chinese_chars:
            for i in range(len(chunk) - 1):
                tokens.append(chunk[i:i+2])
        return tokens


# Export as VectorStore alias for semantic compatibility with existing imports
VectorStore = DocumentStore
