"""Benchmark TensionForge fused_tension OpenCL dispatch vs CPU tension ops.

Profiles inference/tension_forge/ops/fused_tension.py against a TensionLM-style
forward pass to isolate OpenCL overhead from device.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

_LM_DIR = Path(__file__).resolve().parent
_REPO = _LM_DIR.parents[1]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "inference"))

from model import TensionConfig, TensionLM  # noqa: E402


def _cpu_tension_baseline(q: np.ndarray, k: np.ndarray) -> tuple[np.ndarray, float]:
    dim = q.shape[-1]
    scale = float(dim) ** 0.5
    t0 = time.perf_counter()
    scores = np.sum(q * k, axis=-1) / scale
    field = 1.0 / (1.0 + np.exp(-scores))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return field, elapsed_ms


def _torch_forward_baseline(model: TensionLM, x: torch.Tensor, *, iters: int) -> dict:
    model.eval()
    times: list[float] = []
    with torch.no_grad():
        for _ in range(iters):
            t0 = time.perf_counter()
            model(x)
            times.append((time.perf_counter() - t0) * 1000.0)
    return {
        "backend": "torch_cpu" if not torch.cuda.is_available() else "torch_cuda",
        "median_ms": float(np.median(times)),
        "mean_ms": float(np.mean(times)),
        "iters": iters,
    }


def _opencl_fused_benchmark(
    batch: int,
    features: int,
    hidden: int,
    *,
    iters: int,
) -> dict:
    try:
        from inference.tension_forge.device import describe_device, find_opencl_device
        from inference.tension_forge.ops.fused_tension import fused_tension_linear_device
        from inference.tension_forge.runtime import TensionForgeRuntime
        import pyopencl as cl  # noqa: F401
    except ImportError as exc:
        return {"backend": "opencl", "available": False, "error": str(exc)}

    try:
        runtime = TensionForgeRuntime(
            platform_contains="",
            device_contains="",
            profiling=True,
        )
        info = runtime.info
    except Exception as exc:
        return {"backend": "opencl", "available": False, "error": str(exc)}

    rng = np.random.default_rng(0)
    feat = rng.standard_normal((batch, features), dtype=np.float32)
    state = rng.standard_normal((batch, hidden), dtype=np.float32)
    prop_w = rng.standard_normal((features, hidden), dtype=np.float32) * 0.02
    prop_b = np.zeros(hidden, dtype=np.float32)
    gate_w = rng.standard_normal((features, hidden), dtype=np.float32) * 0.02
    gate_b = np.zeros(hidden, dtype=np.float32)

    t0 = time.perf_counter()
    _, meta = fused_tension_linear_device(
        runtime,
        feat,
        state,
        prop_w,
        prop_b,
        gate_w,
        gate_b,
        repetitions=iters,
    )
    wall_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "backend": "opencl_fused_tension",
        "available": True,
        "device": info.to_dict(),
        "wall_ms": wall_ms,
        "kernel_meta": meta,
    }


def run_benchmark(*, batch: int = 8, dim: int = 128, window: int = 8, iters: int = 20) -> dict:
    config = TensionConfig(dim=dim, num_layers=2, num_heads=4, window=window)
    model = TensionLM(config)
    seq = torch.randint(0, min(config.vocab_size, 512), (batch, window + 1))

    torch_stats = _torch_forward_baseline(model, seq, iters=iters)

    q = np.random.randn(batch, dim).astype(np.float32)
    k = np.random.randn(batch, dim).astype(np.float32)
    _, cpu_ms = _cpu_tension_baseline(q, k)

    opencl_stats = _opencl_fused_benchmark(batch, dim, dim, iters=iters)

    kernel_median = None
    if opencl_stats.get("kernel_meta"):
        kernel_median = opencl_stats["kernel_meta"].get("median_kernel_ms")

    overhead_ratio = None
    if kernel_median and cpu_ms > 0:
        overhead_ratio = round(kernel_median / cpu_ms, 4)

    return {
        "config": {"batch": batch, "dim": dim, "window": window, "iters": iters},
        "torch_forward": torch_stats,
        "cpu_tension_sigmoid_ms": cpu_ms,
        "opencl_fused_tension": opencl_stats,
        "opencl_vs_cpu_overhead_ratio": overhead_ratio,
        "throttle_hint": (
            "OpenCL dispatch dominates" if overhead_ratio and overhead_ratio > 5.0
            else "Compute-bound or OpenCL unavailable"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark TensionForge vs TensionLM CPU path")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--window", type=int, default=8)
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    report = run_benchmark(batch=args.batch, dim=args.dim, window=args.window, iters=args.iters)
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n")


if __name__ == "__main__":
    main()