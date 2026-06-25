"""BOGVM-0 — 16-opcode deterministic wave-state virtual machine.

The bedrock of TS-OS computation. All state changes log through .bogpk artifacts.
"""

from pathlib import Path

BOGVM_ROOT = Path(__file__).resolve().parent
BOGVM_PACKAGE = BOGVM_ROOT / "bogvm"

__all__ = ["BOGVM_ROOT", "BOGVM_PACKAGE"]