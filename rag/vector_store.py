"""Vector store auto-selector — ChromaDB preferred, offline keyword fallback.

Detection:
1. Check if chromadb is installed (`pip install chromadb`)
2. Check if the ONNX model file is fully cached (~79MB onnx.tar.gz)
3. If both yes → use ChromaDB (semantic search, better accuracy)
4. If either no  → use offline keyword matching (zero network, zero download)

The ONNX model check is strict: we verify the actual .tar.gz file exists
and is reasonably sized (>50MB), not just the cache directory.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
logger = logging.getLogger(__name__)

# ── Detection ──────────────────────────────────────────────────────

_HAS_CHROMA = False
_ONNX_READY = False

try:
    import chromadb  # noqa: F401
    _HAS_CHROMA = True
except ImportError:
    _HAS_CHROMA = False

# Check if the actual ONNX model file is fully cached
_onnx_file = Path.home() / ".cache" / "chroma" / "onnx_models" / "all-MiniLM-L6-v2" / "onnx.tar.gz"
if _onnx_file.exists() and _onnx_file.stat().st_size > 50_000_000:  # > 50MB
    _ONNX_READY = True

# ── Selection ──────────────────────────────────────────────────────

if _HAS_CHROMA and _ONNX_READY:
    from rag.store_chroma import VectorStore
    logger.info("VectorStore: ChromaDB (ONNX cached, semantic search)")
elif _HAS_CHROMA and not _ONNX_READY:
    logger.warning(
        "VectorStore: ChromaDB installed but ONNX model not fully downloaded.\n"
        "  To enable semantic search, run: python -c \"import chromadb; chromadb.Client()\"\n"
        "  This downloads the ~79MB ONNX model to ~/.cache/chroma/\n"
        "  Falling back to offline keyword matching."
    )
    from rag.store_offline import VectorStore
else:
    logger.info("VectorStore: offline keyword matching (install chromadb for semantic search)")
    from rag.store_offline import VectorStore
