"""
Runtime composition package (`thinking_system.runtime`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from interface.runtime import BoggersRuntime, RuntimeConfig

__all__ = ["BoggersRuntime", "RuntimeConfig"]
