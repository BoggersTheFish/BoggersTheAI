"""
BogVM bytecode execution bridge (`thinking_system.engines.bogvm`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.bogvm_bridge import (
    execute_bogvm_assembly,
    normalize_assembly,
    program_hash_for_assembly,
)

__all__ = ["execute_bogvm_assembly", "normalize_assembly", "program_hash_for_assembly"]
