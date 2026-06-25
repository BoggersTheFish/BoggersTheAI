from __future__ import annotations

from pathlib import Path
import argparse
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.graph.client import NebulaGraphClient

def summarize_result(result: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "succeeded": getattr(result, "is_succeeded", lambda: None)(),
        "error_code": getattr(result, "error_code", lambda: None)(),
        "error_msg": str(getattr(result, "error_msg", lambda: b"")()),
    }
    if hasattr(result, "row_size") and hasattr(result, "row_values"):
        rows: list[str] = []
        try:
            for idx in range(result.row_size()):
                rows.append(str(result.row_values(idx)))
        except Exception as exc:  # pragma: no cover - debug-only path
            rows.append(f"<row-read-error:{exc}>")
        summary["rows"] = rows
    return summary


def ensure_storage_host_registered(client: NebulaGraphClient) -> None:
    hosts_result = client.query_ngql("SHOW HOSTS;")
    host_summary = summarize_result(hosts_result)
    rows = host_summary.get("rows", [])
    if rows:
        return

    add_host_result = client.query_ngql('ADD HOSTS "storaged0":9779;')
    if not getattr(add_host_result, "is_succeeded", lambda: False)():
        raise RuntimeError("Failed to register Nebula storage host.")


def wait_for_space(client: NebulaGraphClient, space_name: str, attempts: int = 20) -> None:
    for attempt in range(1, attempts + 1):
        spaces_result = client.query_ngql("SHOW SPACES;")
        summary = summarize_result(spaces_result)
        rows = summary.get("rows", [])
        names = [row for row in rows if space_name in row]
        if names:
            use_result = client.query_ngql(f"USE {space_name};")
            if getattr(use_result, "is_succeeded", lambda: False)():
                return
        time.sleep(1)

    raise RuntimeError(f"Space {space_name} did not become ready in time.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply NebulaGraph schema scripts.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be applied; do not connect to NebulaGraph.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute against a live NebulaGraph instance (default: dry-run from config).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop ts_graph space if it exists before creating (live only). Ensures full schema apply.",
    )
    args = parser.parse_args()

    root = ROOT
    schema_dir = root / "src" / "graph" / "schema"

    if args.dry_run:
        print("Dry-run mode: would apply schema (no connection to NebulaGraph).")
        for script_name in ("create_space.ngql", "create_schema.ngql"):
            path = schema_dir / script_name
            if not path.exists():
                print(f"  (missing: {path})")
                continue
            statements = [s.strip() for s in path.read_text(encoding="utf-8").split(";") if s.strip()]
            for stmt in statements:
                preview = stmt[:80] + "..." if len(stmt) > 80 else stmt
                print(f"  {script_name}: {preview}")
        print("Run with --live to apply against a running NebulaGraph (e.g. after docker compose up -d).")
        return

    client = NebulaGraphClient(
        root / "configs" / "graph.yaml",
        dry_run_override=not args.live if args.live else None,
    )

    if args.live:
        ensure_storage_host_registered(client)
        if args.reset:
            result = client.query_ngql("DROP SPACE IF EXISTS ts_graph;")
            if not getattr(result, "is_succeeded", lambda: True)():
                raise RuntimeError("Failed to drop space ts_graph.")
            print("Dropped space ts_graph (if it existed). Waiting before recreate...")
            time.sleep(3)

    for script_name in ("create_space.ngql", "create_schema.ngql"):
        statement = (schema_dir / script_name).read_text(encoding="utf-8")
        statements = [item.strip() for item in statement.split(";") if item.strip()]
        for partial in statements:
            result = client.query_ngql(f"{partial};")
            print(f"Applied {script_name}: {partial}")
            if not getattr(result, "is_succeeded", lambda: True)():
                raise RuntimeError(f"Failed statement: {partial}")
            if script_name == "create_space.ngql" and partial.startswith("CREATE SPACE"):
                wait_for_space(client, "ts_graph")

    client.close()


if __name__ == "__main__":
    main()
