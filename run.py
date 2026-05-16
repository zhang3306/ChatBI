"""ChatBI launcher — seed data → index RAG → start UI.

Usage:
    python run.py             # full pipeline
    python run.py --seed      # seed data only
    python run.py --index     # reindex RAG only
    python run.py --ui        # start UI only
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import subprocess
from config import SEED_SCALE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, default=SEED_SCALE, help="Data scale")
    parser.add_argument("--seed", action="store_true", help="Seed data only")
    parser.add_argument("--index", action="store_true", help="Reindex RAG only")
    parser.add_argument("--force", action="store_true", help="Force reindex")
    parser.add_argument("--ui", action="store_true", help="Start UI only")
    args = parser.parse_args()

    root = Path(__file__).parent

    if args.ui:
        _run_ui(root)
        return

    if args.seed:
        _seed_data(root, args.scale)
        return

    if args.index:
        _index_rag(root, args.force)
        return

    # Default: full pipeline
    _seed_data(root, args.scale)
    _index_rag(root, args.force)
    _run_ui(root)


def _seed_data(root: Path, scale: float):
    print(f"[seed] generating data (scale={scale})...")
    subprocess.run([sys.executable, "-m", "db.seed", "--scale", str(scale)],
                   cwd=root, check=True)
    print("[OK] data generation done")


def _index_rag(root: Path, force: bool):
    print("[index] building RAG index...")
    cmd = [sys.executable, "scripts/index.py"]
    if force:
        cmd.append("--force")
    subprocess.run(cmd, cwd=root, check=True)
    print("[OK] RAG index done")


def _run_ui(root: Path):
    print("[ui] starting Streamlit...")
    subprocess.run(["streamlit", "run", "main.py"], cwd=root)


if __name__ == "__main__":
    main()
