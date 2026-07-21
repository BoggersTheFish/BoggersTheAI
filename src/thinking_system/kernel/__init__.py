"""
Canonical Verifier-Gated Transaction Kernel (`thinking_system.kernel`).
"""

from core.kernel.kernel import TSKernel
from core.kernel.receipts import TSReceipt, validate_receipt_hash
from core.kernel.transaction import (
    CommitDecision,
    TransactionRequest,
    TransactionResult,
)

__all__ = [
    "CommitDecision",
    "TSKernel",
    "TSReceipt",
    "TransactionRequest",
    "TransactionResult",
    "validate_receipt_hash",
]
