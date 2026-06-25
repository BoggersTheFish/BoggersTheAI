"""Neural inference layer — TensionLM and TensionForge OpenCL runtime.

Isolates mathematical parity and neural execution from the reasoner and VM bedrock.
"""

from pathlib import Path

INFERENCE_ROOT = Path(__file__).resolve().parent
TENSION_LM_DIR = INFERENCE_ROOT / "tension_lm"
TENSION_FORGE_DIR = INFERENCE_ROOT / "tension_forge"

__all__ = ["INFERENCE_ROOT", "TENSION_LM_DIR", "TENSION_FORGE_DIR"]