"""Document vector store for RAG retrieval.

Default: offline keyword-matching store (zero-download).
If you have network access and want better accuracy, switch to ChromaDB:

    from rag.store_chroma import VectorStore  # requires `pip install chromadb`

Chromadb's ONNX model also requires downloading from HuggingFace (~79MB).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Default: offline keyword store for zero-download usage
from rag.store_offline import VectorStore
