"""
Receipt and proof artifacts package (`thinking_system.artifacts`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.kernel.receipts import TSReceipt, validate_receipt_hash

__all__ = ["TSReceipt", "validate_receipt_hash"]
