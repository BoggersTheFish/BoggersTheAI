"""
Verifier modules & obligation engines (`thinking_system.verifiers`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.kernel.arithmetic import ArithmeticReceipt, SafeArithmeticEvaluator

__all__ = ["SafeArithmeticEvaluator", "ArithmeticReceipt"]
