"""
Thinking System: Verifier-First Research & Engineering Architecture.

Governing Pattern:
  representation
  → lawful quotient
  → relative residual
  → sufficient observer family
  → localised obstruction
  → minimal typed or compositional revision
  → sealed adversarial evaluation

Status: Alpha — canonical monorepo migration in progress.
Many subpackages are COMPATIBILITY_FACADE re-exports over legacy top-level
modules (`core/`, `interface/`, etc.). Prefer explicit imports from the
defining modules for production-critical paths.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure monorepo root is on sys.path for facade imports of legacy packages
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

__version__ = "0.5.0-alpha.1"
__author__ = "Thinking System Contributors"
__display_name__ = "Thinking System"
__slug__ = "thinking-system"

# Kernel exports are the stable public surface. Subpackages are available as
# attributes but not eagerly imported here (avoids pulling runtime/LLM stacks
# on `import thinking_system` and `python -m thinking_system.apps.cli.main`).
from .kernel.kernel import TSKernel
from .kernel.receipts import TSReceipt, validate_receipt_hash
from .kernel.transaction import TransactionResult

__all__ = [
    "__version__",
    "__display_name__",
    "__slug__",
    "apps",
    "artifacts",
    "core",
    "engines",
    "graph",
    "ir",
    "kernel",
    "language",
    "reasoner",
    "runtime",
    "verifiers",
    "TSKernel",
    "TSReceipt",
    "TransactionResult",
    "validate_receipt_hash",
]

_SUBPACKAGES = frozenset(
    {
        "apps",
        "artifacts",
        "core",
        "engines",
        "graph",
        "ir",
        "kernel",
        "language",
        "reasoner",
        "runtime",
        "verifiers",
    }
)


def __getattr__(name: str) -> Any:
    if name in _SUBPACKAGES:
        import importlib

        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
