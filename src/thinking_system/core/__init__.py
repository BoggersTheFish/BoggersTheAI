"""
Core package namespace wrapper (`thinking_system.core`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.ts_engine import TSEngine

__all__ = ["TSEngine"]
