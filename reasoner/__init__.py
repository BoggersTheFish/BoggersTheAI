"""GOAT-TS constraint resolution, Verse Engine, and graph-store hooks.

The reasoner layer proposes; typed verifier support decides acceptance.
"""

from pathlib import Path

REASONER_ROOT = Path(__file__).resolve().parent

__all__ = ["REASONER_ROOT"]
