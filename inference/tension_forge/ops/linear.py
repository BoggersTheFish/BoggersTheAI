from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime


LINEAR_SOURCE = r"""
#ifndef TILE_SIZE
#define TILE_SIZE 16
#endif

__kernel void linear_forward_fp32(
    __global const float *inputs,
    __global const float *weights,
    __global const float *bias,
    __global float *output,
    const unsigned int batch_size,
    const unsigned int input_features,
    const unsigned int output_features
) {
    const unsigned int output_index = get_global_id(0);
    const unsigned int batch_index = get_global_id(1);

    const unsigned int local_column = get_local_id(0);
    const unsigned int local_row = get_local_id(1);

    __local float input_tile[TILE_SIZE][TILE_SIZE];
    __local float weight_tile[TILE_SIZE][TILE_SIZE];

    float accumulator = 0.0f;

    const unsigned int tile_count =
        (
            input_features
            + TILE_SIZE
            - 1
        )
        / TILE_SIZE;

    for (
        unsigned int tile_index = 0;
        tile_index < tile_count;
        ++tile_index
    ) {
        const unsigned int input_index =
            tile_index * TILE_SIZE
            + local_column;

        const unsigned int weight_row =
            tile_index * TILE_SIZE
            + local_row;

        if (
            batch_index < batch_size
            && input_index < input_features
        ) {
            input_tile[local_row][local_column] =
                inputs[
                    batch_index * input_features
                    + input_index
                ];
        } else {
            input_tile[local_row][local_column] =
                0.0f;
        }

        if (
            weight_row < input_features
            && output_index < output_features
        ) {
            weight_tile[local_row][local_column] =
                weights[
                    weight_row * output_features
                    + output_index
                ];
        } else {
            weight_tile[local_row][local_column] =
                0.0f;
        }

        barrier(CLK_LOCAL_MEM_FENCE);

        for (
            unsigned int index = 0;
            index < TILE_SIZE;
            ++index
        ) {
            accumulator +=
                input_tile[local_row][index]
                * weight_tile[index][local_column];
        }

        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (
        batch_index < batch_size
        && output_index < output_features
    ) {
        output[
            batch_index * output_features
            + output_index
        ] =
            accumulator
            + bias[output_index];
    }
}
"""


def linear(
    runtime: TensionForgeRuntime,
    inputs: np.ndarray,
    weights: np.ndarray,
    bias: np.ndarray,
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

    inputs = np.ascontiguousarray(
        inputs,
        dtype=np.float32,
    )

    weights = np.ascontiguousarray(
        weights,
        dtype=np.float32,
    )

    bias = np.ascontiguousarray(
        bias,
        dtype=np.float32,
    )

    if inputs.ndim != 2:
        raise ValueError(
            "inputs must be two-dimensional"
        )

    if weights.ndim != 2:
        raise ValueError(
            "weights must be two-dimensional"
        )

    if bias.ndim != 1:
        raise ValueError(
            "bias must be one-dimensional"
        )

    batch_size, input_features = inputs.shape
    weight_inputs, output_features = weights.shape

    if input_features != weight_inputs:
        raise ValueError(
            "Input and weight dimensions are "
            "incompatible: "
            f"{inputs.shape} and {weights.shape}"
        )

    if bias.shape != (output_features,):
        raise ValueError(
            "Bias shape must match the number of "
            "output features. "
            f"Expected {(output_features,)}, "
            f"received {bias.shape}"
        )

    if (
        batch_size == 0
        or input_features == 0
        or output_features == 0
    ):
        raise ValueError(
            "Linear dimensions must be positive"
        )

    local_work_items = tile_size * tile_size

    if (
        local_work_items
        > runtime.device.max_work_group_size
    ):
        raise ValueError(
            f"Tile size {tile_size} requires "
            f"{local_work_items} work items, but "
            "the device supports at most "
            f"{runtime.device.max_work_group_size}"
        )

    output = np.empty(
        (batch_size, output_features),
        dtype=np.float32,
    )

    inputs_gpu = runtime.buffer_from_host(
        inputs,
        access="read_only",
    )

    weights_gpu = runtime.buffer_from_host(
        weights,
        access="read_only",
    )

    bias_gpu = runtime.buffer_from_host(
        bias,
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
        LINEAR_SOURCE,
        "linear_forward_fp32",
        options=compile_options,
    )

    global_outputs = runtime.round_up(
        output_features,
        tile_size,
    )

    global_batches = runtime.round_up(
        batch_size,
        tile_size,
    )

    arguments = (
        inputs_gpu,
        weights_gpu,
        bias_gpu,
        output_gpu,
        np.uint32(batch_size),
        np.uint32(input_features),
        np.uint32(output_features),
    )

    runtime.run_kernel(
        kernel,
        global_size=(
            global_outputs,
            global_batches,
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
                global_outputs,
                global_batches,
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
        2
        * batch_size
        * input_features
        * output_features
        + batch_size * output_features
    )

    gflops = (
        floating_point_operations
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation": "linear_forward_fp32",
        "input_shape": list(inputs.shape),
        "weight_shape": list(weights.shape),
        "bias_shape": list(bias.shape),
        "output_shape": list(output.shape),
        "tile_size": tile_size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "gflops": gflops,
        "source_sha256":
            runtime.source_hash(LINEAR_SOURCE),
        "compile_options": list(
            compile_options
        ),
    }

    return output, metadata
