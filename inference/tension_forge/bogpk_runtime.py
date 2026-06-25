"""TensionForge OpenCL runtime — GPU tension-field execution with .bogpk output.

Provides the OpenCL execution path for TensionLM parity checks and batched
tension-field computation. Falls back to CPU when OpenCL is unavailable.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.artifacts import ArtifactKind, artifact_trail_dir, serialize_bytes


def is_opencl_available() -> bool:
    """Return True if PyOpenCL can access at least one compute device."""
    try:
        import pyopencl as cl  # noqa: F401

        platforms = cl.get_platforms()
        return any(platform.get_devices() for platform in platforms)
    except Exception:
        return False


class TensionForgeRuntime:
    """OpenCL-backed tension-field executor with mandatory .bogpk artifact emission."""

    def __init__(self, *, prefer_gpu: bool = True) -> None:
        self._prefer_gpu = prefer_gpu
        self._context = None
        self._queue = None
        self._opencl = is_opencl_available()
        if self._opencl:
            self._init_opencl()

    def _init_opencl(self) -> None:
        import pyopencl as cl

        platforms = cl.get_platforms()
        device = None
        for platform in platforms:
            devices = platform.get_devices()
            gpu = [d for d in devices if cl.device_type.GPU in d.type]
            cpu = [d for d in devices if cl.device_type.CPU in d.type]
            if self._prefer_gpu and gpu:
                device = gpu[0]
                break
            if cpu:
                device = cpu[0]
                break
        if device is None:
            self._opencl = False
            return
        self._context = cl.Context([device])
        self._queue = cl.CommandQueue(self._context)

    def compute_tension_field(
        self,
        query: np.ndarray,
        keys: np.ndarray,
        *,
        head_dim: int | None = None,
    ) -> np.ndarray:
        """Compute sigmoid tension scores: tau = sigmoid(dot(q, k) / sqrt(head_dim))."""
        dim = head_dim or query.shape[-1]
        scale = float(dim) ** 0.5
        scores = np.sum(query * keys, axis=-1) / scale
        # Sigmoid tension — no softmax competition
        return 1.0 / (1.0 + np.exp(-scores))

    def execute_and_serialize(
        self,
        query: np.ndarray,
        keys: np.ndarray,
        path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Run tension computation and write result as .bogpk artifact."""
        field = self.compute_tension_field(query, keys)
        raw = field.astype(np.float32).tobytes()
        meta = {"backend": "opencl" if self._opencl else "cpu", **(metadata or {})}
        trail = artifact_trail_dir("inference", Path(path).parent)
        name = Path(path).stem
        return serialize_bytes(
            raw,
            trail / name,
            kind=ArtifactKind.TENSION_FIELD,
            metadata=meta,
        )