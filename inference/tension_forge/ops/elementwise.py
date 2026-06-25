from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import (
    TensionForgeRuntime,
)


SAXPY_SOURCE = r"""
__kernel void saxpy_fp32(
    const float alpha,
    __global const float *a,
    __global const float *b,
    __global float *output,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        output[index] =
            alpha * a[index] + b[index];
    }
}
"""


def saxpy(
    runtime: TensionForgeRuntime,
    *,
    alpha: float,
    a: np.ndarray,
    b: np.ndarray,
    repetitions: int = 1,
    local_size: int = 256,
) -> tuple[np.ndarray, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    a = np.ascontiguousarray(
        a,
        dtype=np.float32,
    )

    b = np.ascontiguousarray(
        b,
        dtype=np.float32,
    )

    if a.shape != b.shape:
        raise ValueError(
            "a and b must have matching shapes"
        )

    if a.ndim != 1:
        raise ValueError(
            "The current SAXPY operation expects "
            "one-dimensional arrays"
        )

    output = np.empty_like(a)

    a_gpu = runtime.buffer_from_host(
        a,
        access="read_only",
    )

    b_gpu = runtime.buffer_from_host(
        b,
        access="read_only",
    )

    output_gpu = runtime.empty_buffer(
        output.nbytes,
        access="write_only",
    )

    kernel = runtime.kernel(
        SAXPY_SOURCE,
        "saxpy_fp32",
    )

    global_size = runtime.round_up(
        a.size,
        local_size,
    )

    arguments = (
        np.float32(alpha),
        a_gpu,
        b_gpu,
        output_gpu,
        np.uint32(a.size),
    )

    runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=arguments,
    )

    timings_ms: list[float] = []

    for _ in range(repetitions):
        elapsed_ms = runtime.run_kernel(
            kernel,
            global_size=(global_size,),
            local_size=(local_size,),
            arguments=arguments,
        )

        if elapsed_ms is not None:
            timings_ms.append(elapsed_ms)

    runtime.read_buffer(
        output,
        output_gpu,
    )

    median_ms = (
        float(np.median(timings_ms))
        if timings_ms
        else None
    )

    bytes_processed = (
        a.size
        * np.dtype(np.float32).itemsize
        * 3
    )

    bandwidth_gbps = (
        bytes_processed
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation": "saxpy_fp32",
        "element_count": int(a.size),
        "alpha": float(alpha),
        "repetitions": repetitions,
        "local_size": local_size,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "source_sha256":
            runtime.source_hash(SAXPY_SOURCE),
    }

    return output, metadata
