from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


FUSED_TENSION_LINEAR_SOURCE = r"""
#ifndef TILE_SIZE
#define TILE_SIZE 16
#endif

__kernel void fused_tension_linear_fp32(
    __global const float *features,
    __global const float *state,
    __global const float *proposal_weights,
    __global const float *proposal_bias,
    __global const float *gate_weights,
    __global const float *gate_bias,
    __global float *output,
    const unsigned int batch_size,
    const unsigned int feature_count,
    const unsigned int hidden_size
) {
    const unsigned int hidden_index =
        get_global_id(0);

    const unsigned int batch_index =
        get_global_id(1);

    const unsigned int local_column =
        get_local_id(0);

    const unsigned int local_row =
        get_local_id(1);

    __local float feature_tile
        [TILE_SIZE][TILE_SIZE];

    __local float proposal_weight_tile
        [TILE_SIZE][TILE_SIZE];

    __local float gate_weight_tile
        [TILE_SIZE][TILE_SIZE];

    float proposal_accumulator = 0.0f;
    float gate_accumulator = 0.0f;

    const unsigned int tile_count =
        (
            feature_count
            + TILE_SIZE
            - 1
        )
        / TILE_SIZE;

    for (
        unsigned int tile_index = 0;
        tile_index < tile_count;
        ++tile_index
    ) {
        const unsigned int feature_index =
            tile_index * TILE_SIZE
            + local_column;

        const unsigned int weight_row =
            tile_index * TILE_SIZE
            + local_row;

        if (
            batch_index < batch_size
            && feature_index < feature_count
        ) {
            feature_tile
                [local_row][local_column] =
                    features[
                        batch_index
                        * feature_count
                        + feature_index
                    ];
        } else {
            feature_tile
                [local_row][local_column] =
                    0.0f;
        }

        if (
            weight_row < feature_count
            && hidden_index < hidden_size
        ) {
            proposal_weight_tile
                [local_row][local_column] =
                    proposal_weights[
                        weight_row
                        * hidden_size
                        + hidden_index
                    ];

            gate_weight_tile
                [local_row][local_column] =
                    gate_weights[
                        weight_row
                        * hidden_size
                        + hidden_index
                    ];
        } else {
            proposal_weight_tile
                [local_row][local_column] =
                    0.0f;

            gate_weight_tile
                [local_row][local_column] =
                    0.0f;
        }

        barrier(CLK_LOCAL_MEM_FENCE);

        for (
            unsigned int index = 0;
            index < TILE_SIZE;
            ++index
        ) {
            const float feature_value =
                feature_tile
                    [local_row][index];

            proposal_accumulator +=
                feature_value
                * proposal_weight_tile
                    [index][local_column];

            gate_accumulator +=
                feature_value
                * gate_weight_tile
                    [index][local_column];
        }

        barrier(CLK_LOCAL_MEM_FENCE);
    }

    if (
        batch_index < batch_size
        && hidden_index < hidden_size
    ) {
        proposal_accumulator +=
            proposal_bias[hidden_index];

        gate_accumulator +=
            gate_bias[hidden_index];

        const float proposal =
            tanh(proposal_accumulator);

        const float gate =
            1.0f
            / (
                1.0f
                + exp(-gate_accumulator)
            );

        const unsigned int output_index =
            batch_index
            * hidden_size
            + hidden_index;

        const float current_state =
            state[output_index];

        output[output_index] =
            current_state
            + gate
            * (
                proposal
                - current_state
            );
    }
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


def fused_tension_linear_device(
    runtime: TensionForgeRuntime,
    features: DeviceTensor,
    state: DeviceTensor,
    proposal_weights: DeviceTensor,
    proposal_bias: DeviceTensor,
    gate_weights: DeviceTensor,
    gate_bias: DeviceTensor,
    *,
    output: DeviceTensor | None = None,
    repetitions: int = 1,
    tile_size: int = 16,
) -> tuple[DeviceTensor, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    if tile_size not in {8, 16}:
        raise ValueError(
            "tile_size must currently be 8 or 16"
        )

    tensors = (
        ("features", features),
        ("state", state),
        ("proposal_weights", proposal_weights),
        ("proposal_bias", proposal_bias),
        ("gate_weights", gate_weights),
        ("gate_bias", gate_bias),
    )

    for name, tensor in tensors:
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if features.ndim != 2:
        raise ValueError(
            "features must be two-dimensional"
        )

    if state.ndim != 2:
        raise ValueError(
            "state must be two-dimensional"
        )

    if proposal_weights.ndim != 2:
        raise ValueError(
            "proposal_weights must be "
            "two-dimensional"
        )

    if gate_weights.ndim != 2:
        raise ValueError(
            "gate_weights must be "
            "two-dimensional"
        )

    if proposal_bias.ndim != 1:
        raise ValueError(
            "proposal_bias must be one-dimensional"
        )

    if gate_bias.ndim != 1:
        raise ValueError(
            "gate_bias must be one-dimensional"
        )

    batch_size, feature_count = features.shape
    state_batch, hidden_size = state.shape

    if state_batch != batch_size:
        raise ValueError(
            "features and state batch dimensions "
            "must match"
        )

    expected_weight_shape = (
        feature_count,
        hidden_size,
    )

    if proposal_weights.shape != (
        expected_weight_shape
    ):
        raise ValueError(
            "proposal_weights shape is incorrect. "
            f"Expected {expected_weight_shape}, "
            f"received {proposal_weights.shape}"
        )

    if gate_weights.shape != expected_weight_shape:
        raise ValueError(
            "gate_weights shape is incorrect. "
            f"Expected {expected_weight_shape}, "
            f"received {gate_weights.shape}"
        )

    expected_bias_shape = (hidden_size,)

    if proposal_bias.shape != expected_bias_shape:
        raise ValueError(
            "proposal_bias shape is incorrect. "
            f"Expected {expected_bias_shape}, "
            f"received {proposal_bias.shape}"
        )

    if gate_bias.shape != expected_bias_shape:
        raise ValueError(
            "gate_bias shape is incorrect. "
            f"Expected {expected_bias_shape}, "
            f"received {gate_bias.shape}"
        )

    output_was_reused = output is not None

    if output is None:
        output = DeviceTensor.empty(
            runtime,
            state.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            output,
            "output",
        )

        if output.shape != state.shape:
            raise ValueError(
                "output shape must match state. "
                f"Expected {state.shape}, "
                f"received {output.shape}"
            )

        if output is state:
            raise ValueError(
                "In-place state updates are not "
                "supported by the timed fused API"
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

    kernel = runtime.kernel(
        FUSED_TENSION_LINEAR_SOURCE,
        "fused_tension_linear_fp32",
        options=compile_options,
    )

    global_hidden = runtime.round_up(
        hidden_size,
        tile_size,
    )

    global_batch = runtime.round_up(
        batch_size,
        tile_size,
    )

    arguments = (
        features.buffer,
        state.buffer,
        proposal_weights.buffer,
        proposal_bias.buffer,
        gate_weights.buffer,
        gate_bias.buffer,
        output.buffer,
        np.uint32(batch_size),
        np.uint32(feature_count),
        np.uint32(hidden_size),
    )

    runtime.run_kernel(
        kernel,
        global_size=(
            global_hidden,
            global_batch,
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
                global_hidden,
                global_batch,
            ),
            local_size=(
                tile_size,
                tile_size,
            ),
            arguments=arguments,
        )

        if elapsed_ms is not None:
            timings_ms.append(elapsed_ms)

    median_ms = (
        float(np.median(timings_ms))
        if timings_ms
        else None
    )

    floating_point_operations = (
        4
        * batch_size
        * feature_count
        * hidden_size
    )

    gflops = (
        floating_point_operations
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation":
            "fused_tension_linear_device_fp32",
        "feature_shape": list(features.shape),
        "state_shape": list(state.shape),
        "output_shape": list(output.shape),
        "tile_size": tile_size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_linear_gflops": gflops,
        "logical_operations_fused": [
            "proposal_linear",
            "proposal_tanh",
            "gate_linear",
            "gate_sigmoid",
            "tension_update",
        ],
        "kernel_launches_per_iteration": 1,
        "unfused_launches_per_iteration": 5,
        "output_buffer_reused":
            output_was_reused,
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(
                FUSED_TENSION_LINEAR_SOURCE
            ),
        "compile_options":
            list(compile_options),
    }

    return output, metadata
