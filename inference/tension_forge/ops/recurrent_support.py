from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


RECURRENT_SUPPORT_SOURCE = r"""
__kernel void concatenate_rows_fp32(
    __global const float *left,
    __global const float *right,
    __global float *output,
    const unsigned int rows,
    const unsigned int left_columns,
    const unsigned int right_columns
) {
    const unsigned int index = get_global_id(0);
    const unsigned int output_columns =
        left_columns + right_columns;
    const unsigned int count =
        rows * output_columns;

    if (index < count) {
        const unsigned int row =
            index / output_columns;

        const unsigned int column =
            index % output_columns;

        if (column < left_columns) {
            output[index] =
                left[
                    row * left_columns
                    + column
                ];
        } else {
            output[index] =
                right[
                    row * right_columns
                    + column
                    - left_columns
                ];
        }
    }
}


__kernel void fill_fp32(
    __global float *destination,
    const float value,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        destination[index] = value;
    }
}


__kernel void add_inplace_fp32(
    __global float *destination,
    __global const float *source,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        destination[index] += source[index];
    }
}


__kernel void merge_recurrent_state_gradient_fp32(
    __global const float *proposal_feature_gradient,
    __global const float *gate_feature_gradient,
    __global const float *direct_state_gradient,
    __global float *output_state_gradient,
    const unsigned int batch_size,
    const unsigned int input_features,
    const unsigned int hidden_size
) {
    const unsigned int index = get_global_id(0);
    const unsigned int count =
        batch_size * hidden_size;

    if (index < count) {
        const unsigned int batch_index =
            index / hidden_size;

        const unsigned int hidden_index =
            index % hidden_size;

        const unsigned int combined_columns =
            input_features + hidden_size;

        const unsigned int combined_index =
            batch_index * combined_columns
            + input_features
            + hidden_index;

        output_state_gradient[index] =
            direct_state_gradient[index]
            + proposal_feature_gradient[
                combined_index
            ]
            + gate_feature_gradient[
                combined_index
            ];
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


def _one_dimensional_launch(
    runtime: TensionForgeRuntime,
    count: int,
) -> tuple[int, int]:
    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        count,
        local_size,
    )

    return global_size, local_size


def concatenate_rows_device(
    runtime: TensionForgeRuntime,
    left: DeviceTensor,
    right: DeviceTensor,
    *,
    output: DeviceTensor | None = None,
) -> tuple[DeviceTensor, dict[str, Any]]:
    _validate_tensor(runtime, left, "left")
    _validate_tensor(runtime, right, "right")

    if left.ndim != 2 or right.ndim != 2:
        raise ValueError(
            "left and right must be two-dimensional"
        )

    if left.shape[0] != right.shape[0]:
        raise ValueError(
            "left and right row counts must match"
        )

    rows = left.shape[0]
    left_columns = left.shape[1]
    right_columns = right.shape[1]

    expected_shape = (
        rows,
        left_columns + right_columns,
    )

    output_reused = output is not None

    if output is None:
        output = DeviceTensor.empty(
            runtime,
            expected_shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            output,
            "output",
        )

        if output.shape != expected_shape:
            raise ValueError(
                "output shape is incorrect. "
                f"Expected {expected_shape}, "
                f"received {output.shape}"
            )

    kernel = runtime.kernel(
        RECURRENT_SUPPORT_SOURCE,
        "concatenate_rows_fp32",
    )

    global_size, local_size = (
        _one_dimensional_launch(
            runtime,
            output.size,
        )
    )

    elapsed_ms = runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=(
            left.buffer,
            right.buffer,
            output.buffer,
            np.uint32(rows),
            np.uint32(left_columns),
            np.uint32(right_columns),
        ),
    )

    return output, {
        "operation":
            "concatenate_rows_device_fp32",
        "left_shape": list(left.shape),
        "right_shape": list(right.shape),
        "output_shape": list(output.shape),
        "output_buffer_reused":
            output_reused,
        "kernel_ms": elapsed_ms,
        "source_sha256":
            runtime.source_hash(
                RECURRENT_SUPPORT_SOURCE
            ),
    }


def fill_device(
    runtime: TensionForgeRuntime,
    destination: DeviceTensor,
    value: float = 0.0,
) -> dict[str, Any]:
    _validate_tensor(
        runtime,
        destination,
        "destination",
    )

    kernel = runtime.kernel(
        RECURRENT_SUPPORT_SOURCE,
        "fill_fp32",
    )

    global_size, local_size = (
        _one_dimensional_launch(
            runtime,
            destination.size,
        )
    )

    elapsed_ms = runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=(
            destination.buffer,
            np.float32(value),
            np.uint32(destination.size),
        ),
    )

    return {
        "operation": "fill_device_fp32",
        "shape": list(destination.shape),
        "value": float(value),
        "kernel_ms": elapsed_ms,
    }


def add_inplace_device(
    runtime: TensionForgeRuntime,
    destination: DeviceTensor,
    source: DeviceTensor,
) -> dict[str, Any]:
    _validate_tensor(
        runtime,
        destination,
        "destination",
    )

    _validate_tensor(
        runtime,
        source,
        "source",
    )

    if destination.shape != source.shape:
        raise ValueError(
            "destination and source shapes "
            "must match"
        )

    kernel = runtime.kernel(
        RECURRENT_SUPPORT_SOURCE,
        "add_inplace_fp32",
    )

    global_size, local_size = (
        _one_dimensional_launch(
            runtime,
            destination.size,
        )
    )

    elapsed_ms = runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=(
            destination.buffer,
            source.buffer,
            np.uint32(destination.size),
        ),
    )

    return {
        "operation":
            "add_inplace_device_fp32",
        "shape": list(destination.shape),
        "kernel_ms": elapsed_ms,
    }


def merge_recurrent_state_gradient_device(
    runtime: TensionForgeRuntime,
    proposal_feature_gradient: DeviceTensor,
    gate_feature_gradient: DeviceTensor,
    direct_state_gradient: DeviceTensor,
    *,
    input_features: int,
    output: DeviceTensor | None = None,
) -> tuple[DeviceTensor, dict[str, Any]]:
    for name, tensor in (
        (
            "proposal_feature_gradient",
            proposal_feature_gradient,
        ),
        (
            "gate_feature_gradient",
            gate_feature_gradient,
        ),
        (
            "direct_state_gradient",
            direct_state_gradient,
        ),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if proposal_feature_gradient.ndim != 2:
        raise ValueError(
            "proposal_feature_gradient must be "
            "two-dimensional"
        )

    if (
        gate_feature_gradient.shape
        != proposal_feature_gradient.shape
    ):
        raise ValueError(
            "proposal and gate feature-gradient "
            "shapes must match"
        )

    if direct_state_gradient.ndim != 2:
        raise ValueError(
            "direct_state_gradient must be "
            "two-dimensional"
        )

    batch_size = (
        proposal_feature_gradient.shape[0]
    )

    if (
        direct_state_gradient.shape[0]
        != batch_size
    ):
        raise ValueError(
            "gradient batch dimensions must match"
        )

    hidden_size = (
        direct_state_gradient.shape[1]
    )

    expected_combined_columns = (
        input_features + hidden_size
    )

    if (
        proposal_feature_gradient.shape[1]
        != expected_combined_columns
    ):
        raise ValueError(
            "feature-gradient width is incorrect. "
            f"Expected {expected_combined_columns}, "
            "received "
            f"{proposal_feature_gradient.shape[1]}"
        )

    output_reused = output is not None

    if output is None:
        output = DeviceTensor.empty(
            runtime,
            direct_state_gradient.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            output,
            "output",
        )

        if (
            output.shape
            != direct_state_gradient.shape
        ):
            raise ValueError(
                "output shape must match direct "
                "state gradient"
            )

    kernel = runtime.kernel(
        RECURRENT_SUPPORT_SOURCE,
        "merge_recurrent_state_gradient_fp32",
    )

    global_size, local_size = (
        _one_dimensional_launch(
            runtime,
            output.size,
        )
    )

    elapsed_ms = runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=(
            proposal_feature_gradient.buffer,
            gate_feature_gradient.buffer,
            direct_state_gradient.buffer,
            output.buffer,
            np.uint32(batch_size),
            np.uint32(input_features),
            np.uint32(hidden_size),
        ),
    )

    return output, {
        "operation":
            "merge_recurrent_state_gradient_fp32",
        "batch_size": batch_size,
        "input_features": input_features,
        "hidden_size": hidden_size,
        "output_buffer_reused":
            output_reused,
        "kernel_ms": elapsed_ms,
    }
