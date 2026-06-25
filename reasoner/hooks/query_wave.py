"""
List concepts (nodes) that belong to a given wave. Use after ingestion to verify wave→concept links.

Usage:
  python scripts/query_wave.py --wave-id <id> [--live]
  python scripts/query_wave.py --list [--live]   # list recent waves, then pick one
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.client import NebulaGraphClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Query concepts in a wave.")
    parser.add_argument("--wave-id", help="Wave ID (e.g. from list_waves or ingestion).")
    parser.add_argument("--list", action="store_true", help="List recent waves (up to 20) and exit.")
    parser.add_argument("--live", action="store_true", help="Query live NebulaGraph (default: dry-run).")
    parser.add_argument("--limit", type=int, default=500, help="Max concepts to return (default 500).")
    args = parser.parse_args()

    client = NebulaGraphClient(
        ROOT / "configs" / "graph.yaml",
        dry_run_override=not args.live if args.live else None,
    )
    try:
        if args.list:
            waves = client.list_waves(limit=20)
            if not waves:
                print("No waves found. Run ingestion with --live first.")
                return
            print(f"Found {len(waves)} wave(s):")
            for w in waves:
                print(f"  {w.wave_id}  source={w.source}  label={w.label[:60]}...")
            return

        if not args.wave_id:
            print("Provide --wave-id <id> or use --list to see wave IDs.")
            sys.exit(1)

        edges = client.list_in_wave_edges(wave_id=args.wave_id, limit=args.limit)
        concept_ids = list({e.src_id for e in edges})
        if not concept_ids:
            print(f"No concepts linked to wave {args.wave_id}.")
            return
        nodes = client.get_nodes_by_ids(concept_ids)
        labels = [n.label for n in nodes if n]
        print(f"Wave {args.wave_id}: {len(labels)} concept(s)")
        for lab in sorted(labels)[:200]:
            print(f"  {lab}")
        if len(labels) > 200:
            print(f"  ... and {len(labels) - 200} more")
    finally:
        client.close()


if __name__ == "__main__":
    main()
