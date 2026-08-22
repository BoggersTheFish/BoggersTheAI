"""Canonical verifier-gated TS transaction kernel."""

from .kernel import TSKernel
from .prime_authority import (
    AUTHORITY_MODE_LEGACY_LOCAL,
    AUTHORITY_MODE_PRIME_REQUIRED,
    PrimeAdmission,
    PrimeAuthorityError,
    PrimeAuthorityUnavailable,
    PrimeV19AuthorityAdapter,
)
from .receipts import TSReceipt, validate_receipt_hash
from .transaction import (
    CommitDecision,
    ReentrantGraphTransactionError,
    TransactionRequest,
    TransactionResult,
)

__all__ = [
    "CommitDecision",
    "AUTHORITY_MODE_LEGACY_LOCAL",
    "AUTHORITY_MODE_PRIME_REQUIRED",
    "PrimeAdmission",
    "PrimeAuthorityError",
    "PrimeAuthorityUnavailable",
    "PrimeV19AuthorityAdapter",
    "ReentrantGraphTransactionError",
    "TSKernel",
    "TSReceipt",
    "TransactionRequest",
    "TransactionResult",
    "validate_receipt_hash",
]
