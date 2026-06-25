from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime


MATMUL_SOURCE = r"""
#ifndef TILE_SIZE
#define TILE_SIZE 16
#endif

__kernel void matmul_tiled_fp32(
    __global const float *a,
    __global const float *b,
    __global float *output,
    const unsigned int rows,
    const unsigned int inner,
    const unsigned int columns
) {
    const unsigned int column = get_global_id(0);
    const unsigned int row = get_global_id(1);

    const unsigned int local_column = get_local_id(0);
    const unsigned int local_row = get_local_id(1);

    __local float tile_a[TILE_SIZE][TILE_SIZE];
    __local float tile_b[TILE_SIZE][TILE_SIZE];

    float accumulator = 0.0f;

    const unsigned int tile_count =
        (inner + TILE_SIZE - 1) / TILE_SIZE;

    for (
        unsigned int tile_index = 0;
        tile_index < tile_count;
        ++tile_index
    ) {
        const unsigned int a_column =
            tile_index * TILE_SIZE + local_column;

        const unsigned int b_row =
            tile_index * TILE_SIZE + local_row;

        if (row < rows && a_column < inner) {
            tile_a[local_row][local_column] =
                a[row * inner + a_column];
        } else {
            tile_a[local_row][local_column] = 0.0f;
        }

        if (b_row < inner && column < columns) {
            tile_b[local_row][local_column] =
                b[b_row * columns + column];
        } else {
            tile_b[local_row][local_column] = 0.0f;
        }

        barrier(CLK_LOCAL_MEM_FENCE);

        for (
            unsigned int index = 0;
            index < TILE_SIZE;
            ++index
        ) {
            accumulator +=
                tile_a[local_row][index]
                * tile_b[index][local_column];
        }

        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (row < rows && column < columns) {
        output[row * columns + column] =
            accumulator;
    }
}
"""


def matmul(
    runtime: TensionForgeRuntime,
    a: np.ndarray,
    b: np.ndarray,
    *,
    repetitions: int = 1,
    tile_size: int = 16,
) -> tuple[np.ndarray, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    if tile_size not in {8, 16}:
        raise ValueError(
            "tile_size must currently be 8 or 16"
        )

    a = np.ascontiguousarray(
        a,
        dtype=np.float32,
    )

    b = np.ascontiguousarray(
        b,
        dtype=np.float32,
    )

    if a.ndim != 2 or b.ndim != 2:
        raise ValueError(
            "matmul expects two-dimensional arrays"
        )

    rows, inner = a.shape
    b_inner, columns = b.shape

    if inner != b_inner:
        raise ValueError(
            "Incompatible matrix dimensions: "
            f"{a.shape} cannot be multiplied by "
            f"{b.shape}"
        )

    if rows == 0 or inner == 0 or columns == 0:
        raise ValueError(
            "Matrix dimensions must be positive"
        )

    local_work_items = tile_size * tile_size

    if local_work_items > runtime.device.max_work_group_size:
        raise ValueError(
            f"Tile size {tile_size} requires "
            f"{local_work_items} work items, but the "
            "device supports at most "
            f"{runtime.device.max_work_group_size}"
        )

    output = np.empty(
        (rows, columns),
        dtype=np.float32,
    )

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

    compile_options = (
        f"-DTILE_SIZE={tile_size}",
    )

    kernel = runtime.kernel(
        MATMUL_SOURCE,
        "matmul_tiled_fp32",
        options=compile_options,
    )

    global_columns = runtime.round_up(
        columns,
        tile_size,
    )

    global_rows = runtime.round_up(
        rows,
        tile_size,
    )

    arguments = (
        a_gpu,
        b_gpu,
        output_gpu,
        np.uint32(rows),
        np.uint32(inner),
        np.uint32(columns),
    )

    runtime.run_kernel(
        kernel,
        global_size=(
            global_columns,
            global_rows,
        ),
        local_size=(
            tile_size,
            tile_size,
        ),
        arguments=arguments,
    )

    timings_ms: list[float] = []

    for _ in range(repetitions):
        elapsed_ms = runtime.run_kernel(
            kernel,
            global_size=(
                global_columns,
                global_rows,
            ),
            local_size=(
                tile_size,
                tile_size,
            ),
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

    floating_point_operations = (
        2 * rows * inner * columns
    )

    gflops = (
        floating_point_operations
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation": "matmul_tiled_fp32",
        "a_shape": list(a.shape),
        "b_shape": list(b.shape),
        "output_shape": list(output.shape),
        "tile_size": tile_size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "gflops": gflops,
        "source_sha256":
            runtime.source_hash(MATMUL_SOURCE),
        "compile_options": list(compile_options),
    }

    return output, metadata
