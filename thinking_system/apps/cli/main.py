"""
CLI entrypoint wrapper under thinking_system package namespace.
"""

from apps.cli.main import main, run_legacy_chat, run_legacy_dashboard

__all__ = ["main", "run_legacy_chat", "run_legacy_dashboard"]
