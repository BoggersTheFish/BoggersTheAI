from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


ACTIVATION_SOURCE = r"""
__kernel void tanh_fp32(
    __global const float *input,
    __global float *output,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        output[index] = tanh(input[index]);
    }
}


__kernel void sigmoid_fp32(
    __global const float *input,
    __global float *output,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float value = input[index];
        output[index] = 1.0f / (1.0f + exp(-value));
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


def _unary_activation_device(
    runtime: TensionForgeRuntime,
    input_tensor: DeviceTensor,
    *,
    kernel_name: str,
    operation_name: str,
    output: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    _validate_tensor(
        runtime,
        input_tensor,
        "input_tensor",
    )

    output_was_reused = output is not None

    if output is None:
        output = DeviceTensor.empty(
            runtime,
            input_tensor.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            output,
            "output",
        )

        if output.shape != input_tensor.shape:
            raise ValueError(
                "Output shape must match input shape. "
                f"Expected {input_tensor.shape}, "
                f"received {output.shape}"
            )

    kernel = runtime.kernel(
        ACTIVATION_SOURCE,
        kernel_name,
    )

    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        input_tensor.size,
        local_size,
    )

    arguments = (
        input_tensor.buffer,
        output.buffer,
        np.uint32(input_tensor.size),
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

    median_ms = (
        float(np.median(timings_ms))
        if timings_ms
        else None
    )

    bytes_processed = (
        input_tensor.nbytes
        + output.nbytes
    )

    bandwidth_gbps = (
        bytes_processed
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation": operation_name,
        "shape": list(input_tensor.shape),
        "element_count": input_tensor.size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "output_buffer_reused":
            output_was_reused,
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(
                ACTIVATION_SOURCE
            ),
    }

    return output, metadata


def tanh_device(
    runtime: TensionForgeRuntime,
    input_tensor: DeviceTensor,
    *,
    output: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    return _unary_activation_device(
        runtime,
        input_tensor,
        kernel_name="tanh_fp32",
        operation_name="tanh_device_fp32",
        output=output,
        repetitions=repetitions,
    )


def sigmoid_device(
    runtime: TensionForgeRuntime,
    input_tensor: DeviceTensor,
    *,
    output: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    return _unary_activation_device(
        runtime,
        input_tensor,
        kernel_name="sigmoid_fp32",
        operation_name="sigmoid_device_fp32",
        output=output,
        repetitions=repetitions,
    )
