"""Unified retriever — fetches relevant schemas, relationships, and SQL examples."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SCHEMA_COLLECTION, EXAMPLE_COLLECTION, TOP_K_SCHEMAS, TOP_K_EXAMPLES
from rag.vector_store import VectorStore


class Retriever:
    """RAG retriever using keyword matching for offline availability."""

    def __init__(self, vs: VectorStore):
        self.vs = vs

    def retrieve(self, question: str) -> dict:
        """Get relevant schemas, relationships, and SQL examples for a question.

        Returns:
            {"schemas": [...], "relationships": [...], "examples": [...]}
        """
        schema_results = self.vs.query(SCHEMA_COLLECTION, question, n_results=TOP_K_SCHEMAS)

        schemas = []
        relationships = []
        if schema_results.get("documents") and schema_results["documents"][0]:
            for i, doc in enumerate(schema_results["documents"][0]):
                meta = schema_results["metadatas"][0][i] if schema_results.get("metadatas") else {}
                entry = {
                    "id": schema_results["ids"][0][i] if schema_results.get("ids") else "",
                    "text": doc,
                    "distance": schema_results["distances"][0][i] if schema_results.get("distances") else 0,
                }
                if meta.get("type") == "relationship":
                    entry["table"] = meta.get("from_table", "")
                    entry["target_table"] = meta.get("to_table", "")
                    relationships.append(entry)
                else:
                    entry["table"] = meta.get("table", "")
                    schemas.append(entry)

        example_results = self.vs.query(EXAMPLE_COLLECTION, question, n_results=TOP_K_EXAMPLES)
        examples = []
        if example_results.get("documents") and example_results["documents"][0]:
            for i, doc in enumerate(example_results["documents"][0]):
                meta = example_results["metadatas"][0][i] if example_results.get("metadatas") else {}
                examples.append({
                    "id": example_results["ids"][0][i],
                    "text": doc,
                    "question": meta.get("question", ""),
                    "distance": example_results["distances"][0][i],
                })

        return {"schemas": schemas, "relationships": relationships, "examples": examples}
