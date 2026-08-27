"""Legacy re-export of the canonical Thinking System CLI."""

from thinking_system.apps.cli.main import main, run_legacy_chat, run_legacy_dashboard

__all__ = ["main", "run_legacy_chat", "run_legacy_dashboard"]

if __name__ == "__main__":
    raise SystemExit(main())
