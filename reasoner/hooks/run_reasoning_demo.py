from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reasoning.loop import run_reasoning_loop


def main() -> None:
    # Avoid UnicodeEncodeError on Windows when output contains non-ASCII (e.g. ł, ą)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Run a reasoning-loop demo query.")
    parser.add_argument(
        "--query",
        default="Wikipedia supports free knowledge and Wikidata supports structured facts.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Read graph context from the live NebulaGraph instance.",
    )
    args = parser.parse_args()

    response = run_reasoning_loop(args.query, ROOT, live=args.live)
    print(
        {
            "query": response.query,
            "activated_nodes": response.activated_nodes,
            "tension_score": response.tension.score,
            "hypotheses": [hypothesis.prompt for hypothesis in response.hypotheses],
            "graph_context": response.graph_context,
            "live": args.live,
        }
    )


if __name__ == "__main__":
    main()
