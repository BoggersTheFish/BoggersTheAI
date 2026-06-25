from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


LINEAR_BACKWARD_SOURCE = r"""
#ifndef TILE_SIZE
#define TILE_SIZE 16
#endif


__kernel void linear_grad_input_fp32(
    __global const float *grad_output,
    __global const float *weights,
    __global float *grad_input,
    const unsigned int batch_size,
    const unsigned int input_features,
    const unsigned int output_features
) {
    const unsigned int input_index =
        get_global_id(0);

    const unsigned int batch_index =
        get_global_id(1);

    const unsigned int local_column =
        get_local_id(0);

    const unsigned int local_row =
        get_local_id(1);

    __local float grad_tile
        [TILE_SIZE][TILE_SIZE];

    __local float weight_tile
        [TILE_SIZE][TILE_SIZE];

    float accumulator = 0.0f;

    const unsigned int tile_count =
        (
            output_features
            + TILE_SIZE
            - 1
        )
        / TILE_SIZE;

    for (
        unsigned int tile_index = 0;
        tile_index < tile_count;
        ++tile_index
    ) {
        const unsigned int output_column =
            tile_index * TILE_SIZE
            + local_column;

        const unsigned int output_row =
            tile_index * TILE_SIZE
            + local_row;

        if (
            batch_index < batch_size
            && output_column < output_features
        ) {
            grad_tile
                [local_row][local_column] =
                    grad_output[
                        batch_index
                        * output_features
                        + output_column
                    ];
        } else {
            grad_tile
                [local_row][local_column] =
                    0.0f;
        }

        if (
            input_index < input_features
            && output_row < output_features
        ) {
            weight_tile
                [local_row][local_column] =
                    weights[
                        input_index
                        * output_features
                        + output_row
                    ];
        } else {
            weight_tile
                [local_row][local_column] =
                    0.0f;
        }

        barrier(CLK_LOCAL_MEM_FENCE);

        for (
            unsigned int index = 0;
            index < TILE_SIZE;
            ++index
        ) {
            accumulator +=
                grad_tile[local_row][index]
                * weight_tile[index][local_column];
        }

        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (
        batch_index < batch_size
        && input_index < input_features
    ) {
        grad_input[
            batch_index
            * input_features
            + input_index
        ] = accumulator;
    }
}


__kernel void linear_grad_weights_fp32(
    __global const float *inputs,
    __global const float *grad_output,
    __global float *grad_weights,
    const unsigned int batch_size,
    const unsigned int input_features,
    const unsigned int output_features
) {
    const unsigned int output_index =
        get_global_id(0);

    const unsigned int input_index =
        get_global_id(1);

    const unsigned int local_column =
        get_local_id(0);

    const unsigned int local_row =
        get_local_id(1);

    __local float input_tile
        [TILE_SIZE][TILE_SIZE];

    __local float grad_tile
        [TILE_SIZE][TILE_SIZE];

    float accumulator = 0.0f;

    const unsigned int tile_count =
        (
            batch_size
            + TILE_SIZE
            - 1
        )
        / TILE_SIZE;

    for (
        unsigned int tile_index = 0;
        tile_index < tile_count;
        ++tile_index
    ) {
        const unsigned int sample_column =
            tile_index * TILE_SIZE
            + local_column;

        const unsigned int sample_row =
            tile_index * TILE_SIZE
            + local_row;

        if (
            input_index < input_features
            && sample_column < batch_size
        ) {
            input_tile
                [local_row][local_column] =
                    inputs[
                        sample_column
                        * input_features
                        + input_index
                    ];
        } else {
            input_tile
                [local_row][local_column] =
                    0.0f;
        }

        if (
            sample_row < batch_size
            && output_index < output_features
        ) {
            grad_tile
                [local_row][local_column] =
                    grad_output[
                        sample_row
                        * output_features
                        + output_index
                    ];
        } else {
            grad_tile
                [local_row][local_column] =
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
                * grad_tile[index][local_column];
        }

        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (
        input_index < input_features
        && output_index < output_features
    ) {
        grad_weights[
            input_index
            * output_features
            + output_index
        ] = accumulator;
    }
}


__kernel void linear_grad_bias_fp32(
    __global const float *grad_output,
    __global float *grad_bias,
    const unsigned int batch_size,
    const unsigned int output_features
) {
    const unsigned int output_index =
        get_global_id(0);

    if (output_index >= output_features) {
        return;
    }

    float accumulator = 0.0f;

    for (
        unsigned int batch_index = 0;
        batch_index < batch_size;
        ++batch_index
    ) {
        accumulator +=
            grad_output[
                batch_index
                * output_features
                + output_index
            ];
    }

    grad_bias[output_index] = accumulator;
}
"""


def _validate_tensor(
    runtime: TensionForgeRuntime,
    tensor: DeviceTensor,
    name: str,
) -> None:
    if tensor.runtime is not runtime:
        raise ValueError(
            f"{name} belongs to a different runtime"
        )

    if tensor.dtype != np.dtype(np.float32):
        raise ValueError(
            f"{name} must use float32, received "
            f"{tensor.dtype}"
        )


def linear_backward_device(
    runtime: TensionForgeRuntime,
    inputs: DeviceTensor,
    weights: DeviceTensor,
    grad_output: DeviceTensor,
    *,
    grad_input: DeviceTensor | None = None,
    grad_weights: DeviceTensor | None = None,
    grad_bias: DeviceTensor | None = None,
    repetitions: int = 1,
    tile_size: int = 16,
) -> tuple[
    DeviceTensor,
    DeviceTensor,
    DeviceTensor,
    dict[str, Any],
]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    if tile_size not in {8, 16}:
        raise ValueError(
            "tile_size must currently be 8 or 16"
        )

    for name, tensor in (
        ("inputs", inputs),
        ("weights", weights),
        ("grad_output", grad_output),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if inputs.ndim != 2:
        raise ValueError(
            "inputs must be two-dimensional"
        )

    if weights.ndim != 2:
        raise ValueError(
            "weights must be two-dimensional"
        )

    if grad_output.ndim != 2:
        raise ValueError(
            "grad_output must be two-dimensional"
        )

    batch_size, input_features = inputs.shape
    weight_inputs, output_features = weights.shape

    if weight_inputs != input_features:
        raise ValueError(
            "Input and weight dimensions are "
            "incompatible"
        )

    expected_grad_output_shape = (
        batch_size,
        output_features,
    )

    if grad_output.shape != expected_grad_output_shape:
        raise ValueError(
            "grad_output shape is incorrect. "
            f"Expected {expected_grad_output_shape}, "
            f"received {grad_output.shape}"
        )

    expected_grad_input_shape = inputs.shape
    expected_grad_weights_shape = weights.shape
    expected_grad_bias_shape = (output_features,)

    grad_input_reused = grad_input is not None
    grad_weights_reused = grad_weights is not None
    grad_bias_reused = grad_bias is not None

    if grad_input is None:
        grad_input = DeviceTensor.empty(
            runtime,
            expected_grad_input_shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            grad_input,
            "grad_input",
        )

        if grad_input.shape != expected_grad_input_shape:
            raise ValueError(
                "grad_input shape is incorrect"
            )

    if grad_weights is None:
        grad_weights = DeviceTensor.empty(
            runtime,
            expected_grad_weights_shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            grad_weights,
            "grad_weights",
        )

        if (
            grad_weights.shape
            != expected_grad_weights_shape
        ):
            raise ValueError(
                "grad_weights shape is incorrect"
            )

    if grad_bias is None:
        grad_bias = DeviceTensor.empty(
            runtime,
            expected_grad_bias_shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            grad_bias,
            "grad_bias",
        )

        if grad_bias.shape != expected_grad_bias_shape:
            raise ValueError(
                "grad_bias shape is incorrect"
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

    compile_options = (
        f"-DTILE_SIZE={tile_size}",
    )

    grad_input_kernel = runtime.kernel(
        LINEAR_BACKWARD_SOURCE,
        "linear_grad_input_fp32",
        options=compile_options,
    )

    grad_weights_kernel = runtime.kernel(
        LINEAR_BACKWARD_SOURCE,
        "linear_grad_weights_fp32",
        options=compile_options,
    )

    grad_bias_kernel = runtime.kernel(
        LINEAR_BACKWARD_SOURCE,
        "linear_grad_bias_fp32",
        options=compile_options,
    )

    grad_input_global = (
        runtime.round_up(
            input_features,
            tile_size,
        ),
        runtime.round_up(
            batch_size,
            tile_size,
        ),
    )

    grad_weights_global = (
        runtime.round_up(
            output_features,
            tile_size,
        ),
        runtime.round_up(
            input_features,
            tile_size,
        ),
    )

    bias_local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    grad_bias_global = (
        runtime.round_up(
            output_features,
            bias_local_size,
        ),
    )

    grad_input_arguments = (
        grad_output.buffer,
        weights.buffer,
        grad_input.buffer,
        np.uint32(batch_size),
        np.uint32(input_features),
        np.uint32(output_features),
    )

    grad_weights_arguments = (
        inputs.buffer,
        grad_output.buffer,
        grad_weights.buffer,
        np.uint32(batch_size),
        np.uint32(input_features),
        np.uint32(output_features),
    )

    grad_bias_arguments = (
        grad_output.buffer,
        grad_bias.buffer,
        np.uint32(batch_size),
        np.uint32(output_features),
    )

    runtime.run_kernel(
        grad_input_kernel,
        global_size=grad_input_global,
        local_size=(
            tile_size,
            tile_size,
        ),
        arguments=grad_input_arguments,
    )

    runtime.run_kernel(
        grad_weights_kernel,
        global_size=grad_weights_global,
        local_size=(
            tile_size,
            tile_size,
        ),
        arguments=grad_weights_arguments,
    )

    runtime.run_kernel(
        grad_bias_kernel,
        global_size=grad_bias_global,
        local_size=(bias_local_size,),
        arguments=grad_bias_arguments,
    )

    grad_input_times: list[float] = []
    grad_weights_times: list[float] = []
    grad_bias_times: list[float] = []

    for _ in range(repetitions):
        elapsed = runtime.run_kernel(
            grad_input_kernel,
            global_size=grad_input_global,
            local_size=(
                tile_size,
                tile_size,
            ),
            arguments=grad_input_arguments,
        )

        if elapsed is not None:
            grad_input_times.append(elapsed)

        elapsed = runtime.run_kernel(
            grad_weights_kernel,
            global_size=grad_weights_global,
            local_size=(
                tile_size,
                tile_size,
            ),
            arguments=grad_weights_arguments,
        )

        if elapsed is not None:
            grad_weights_times.append(elapsed)

        elapsed = runtime.run_kernel(
            grad_bias_kernel,
            global_size=grad_bias_global,
            local_size=(bias_local_size,),
            arguments=grad_bias_arguments,
        )

        if elapsed is not None:
            grad_bias_times.append(elapsed)

    grad_input_ms = (
        float(np.median(grad_input_times))
        if grad_input_times
        else None
    )

    grad_weights_ms = (
        float(np.median(grad_weights_times))
        if grad_weights_times
        else None
    )

    grad_bias_ms = (
        float(np.median(grad_bias_times))
        if grad_bias_times
        else None
    )

    combined_ms = (
        grad_input_ms
        + grad_weights_ms
        + grad_bias_ms
        if (
            grad_input_ms is not None
            and grad_weights_ms is not None
            and grad_bias_ms is not None
        )
        else None
    )

    matmul_operations = (
        2
        * batch_size
        * input_features
        * output_features
        * 2
    )

    approximate_gflops = (
        matmul_operations
        / (combined_ms * 1e-3)
        / 1e9
        if combined_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation":
            "linear_backward_device_fp32",
        "input_shape": list(inputs.shape),
        "weight_shape": list(weights.shape),
        "grad_output_shape":
            list(grad_output.shape),
        "grad_input_shape":
            list(grad_input.shape),
        "grad_weights_shape":
            list(grad_weights.shape),
        "grad_bias_shape":
            list(grad_bias.shape),
        "tile_size": tile_size,
        "repetitions": repetitions,
        "grad_input_median_ms":
            grad_input_ms,
        "grad_weights_median_ms":
            grad_weights_ms,
        "grad_bias_median_ms":
            grad_bias_ms,
        "combined_median_ms":
            combined_ms,
        "approximate_matmul_gflops":
            approximate_gflops,
        "kernel_launches_per_backward": 3,
        "host_transfers_during_repetitions": 0,
        "buffers_reused": {
            "grad_input": grad_input_reused,
            "grad_weights": grad_weights_reused,
            "grad_bias": grad_bias_reused,
        },
        "source_sha256":
            runtime.source_hash(
                LINEAR_BACKWARD_SOURCE
            ),
        "compile_options":
            list(compile_options),
    }

    return (
        grad_input,
        grad_weights,
        grad_bias,
        metadata,
    )
