from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from info2idea.server import serve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Info2Idea local dashboard.")
    parser.add_argument("--db", default=str(ROOT / "data" / "info2idea.db"))
    parser.add_argument("--sources", default=str(ROOT / "config" / "sources.json"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    serve(host=args.host, port=args.port, db_path=args.db, sources_path=args.sources)


if __name__ == "__main__":
    main()
