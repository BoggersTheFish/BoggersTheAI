#!/usr/bin/env python3
"""
Thinking System Canonical CLI Entrypoint (`ts`).

Provides access to:
  - ts demo      : Run canonical offline verifier-gated transaction & receipt replay demo
  - ts chat      : Run interactive chat interface (TSLC / DDS)
  - ts replay    : Audit and replay a receipt file
  - ts benchmark : Run audit-first benchmark suite
  - ts version   : Display Thinking System version & authority boundary statement
"""

import sys
import json
import argparse
from typing import Sequence

from core.kernel.demo import main as run_kernel_demo
from core.kernel.replay import replay_receipt
from core.kernel.receipts import validate_receipt_hash


def run_demo(args: argparse.Namespace) -> int:
    """Run the canonical verifier-first offline demonstration."""
    print("========================================================================")
    print("Thinking System — Verifier-First Research & Engineering Programme")
    print("========================================================================")
    print("Executing verifier-gated transaction pipeline under residual accounting...\n")
    
    # Run the deterministic kernel demo
    sys_argv_backup = sys.argv
    sys.argv = ["ts-demo"]
    if getattr(args, "json", False):
        sys.argv.append("--json")
    try:
        run_kernel_demo()
    finally:
        sys.argv = sys_argv_backup
    return 0


def run_replay(args: argparse.Namespace) -> int:
    """Replay and verify an execution receipt."""
    receipt_file = args.receipt_file
    print(f"Auditing receipt file: {receipt_file}")
    with open(receipt_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    valid_hash = validate_receipt_hash(data)
    res = {
        "receipt_file": receipt_file,
        "receipt_hash": data.get("receipt_hash"),
        "hash_verified": valid_hash,
        "commit_decision": data.get("commit_decision"),
    }
    print(json.dumps(res, indent=2))
    return 0 if valid_hash else 1


def run_legacy_chat() -> int:
    """Legacy compatibility wrapper for 'boggers' command."""
    from interface.chat import run_chat
    run_chat()
    return 0


def run_legacy_dashboard() -> int:
    """Legacy compatibility wrapper for 'dashboard-start' command."""
    from dashboard.app import main as run_dashboard
    run_dashboard()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ts",
        description="Thinking System: Verifier-first research & engineering architecture.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: demo
    demo_parser = subparsers.add_parser("demo", help="Run canonical offline verifier-gated demo")
    demo_parser.add_argument("--json", action="store_true", help="Output raw JSON receipts")

    # Command: replay
    replay_parser = subparsers.add_parser("replay", help="Audit and replay a transaction receipt")
    replay_parser.add_argument("receipt_file", help="Path to receipt JSON file")

    # Command: chat
    chat_parser = subparsers.add_parser("chat", help="Run interactive chat interface")

    # Command: version
    version_parser = subparsers.add_parser("version", help="Show version and authority boundary")

    args = parser.parse_args(argv)

    if args.command == "demo" or args.command is None:
        return run_demo(args if args.command else parser.parse_args(["demo"]))
    elif args.command == "replay":
        return run_replay(args)
    elif args.command == "chat":
        return run_legacy_chat()
    elif args.command == "version":
        print("Thinking System v1.0.0 (slug: thinking-system, namespace: thinking_system)")
        print("Authority Boundary: Generated language is NOT proof. State transitions are verifier-gated.")
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
