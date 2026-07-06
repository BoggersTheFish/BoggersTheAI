"""Kernel-specific exceptions."""


class TSKernelError(Exception):
    """Base exception for canonical TS kernel failures."""


class RepresentationError(TSKernelError):
    """Raised when TSIR construction or validation fails."""


class VerificationError(TSKernelError):
    """Raised when a verifier channel cannot complete."""


class CommitError(TSKernelError):
    """Raised when atomic commit fails."""
