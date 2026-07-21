"""
TSLC language compiler & dialogue substrate (`thinking_system.language`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.kernel.representation import DeterministicTSParser, ParseResult

__all__ = ["DeterministicTSParser", "ParseResult"]
