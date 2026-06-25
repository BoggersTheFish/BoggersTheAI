from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


BACKWARD_SOURCE = r"""
__kernel void tanh_backward_fp32(
    __global const float *output,
    __global const float *grad_output,
    __global float *grad_input,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float output_value = output[index];

        grad_input[index] =
            grad_output[index]
            * (
                1.0f
                - output_value
                * output_value
            );
    }
}


__kernel void sigmoid_backward_fp32(
    __global const float *output,
    __global const float *grad_output,
    __global float *grad_input,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float output_value = output[index];

        grad_input[index] =
            grad_output[index]
            * output_value
            * (
                1.0f
                - output_value
            );
    }
}


__kernel void tension_update_backward_fp32(
    __global const float *state,
    __global const float *proposal,
    __global const float *gate,
    __global const float *grad_output,
    __global float *grad_state,
    __global float *grad_proposal,
    __global float *grad_gate,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float upstream = grad_output[index];
        const float gate_value = gate[index];

        grad_state[index] =
            upstream
            * (
                1.0f
                - gate_value
            );

        grad_proposal[index] =
            upstream
            * gate_value;

        grad_gate[index] =
            upstream
            * (
                proposal[index]
                - state[index]
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


def _activation_backward_device(
    runtime: TensionForgeRuntime,
    output: DeviceTensor,
    grad_output: DeviceTensor,
    *,
    kernel_name: str,
    operation_name: str,
    grad_input: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    _validate_tensor(
        runtime,
        output,
        "output",
    )

    _validate_tensor(
        runtime,
        grad_output,
        "grad_output",
    )

    if output.shape != grad_output.shape:
        raise ValueError(
            "output and grad_output shapes must match"
        )

    buffer_reused = grad_input is not None

    if grad_input is None:
        grad_input = DeviceTensor.empty(
            runtime,
            output.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            grad_input,
            "grad_input",
        )

        if grad_input.shape != output.shape:
            raise ValueError(
                "grad_input shape must match output"
            )

    kernel = runtime.kernel(
        BACKWARD_SOURCE,
        kernel_name,
    )

    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        output.size,
        local_size,
    )

    arguments = (
        output.buffer,
        grad_output.buffer,
        grad_input.buffer,
        np.uint32(output.size),
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
        output.nbytes
        + grad_output.nbytes
        + grad_input.nbytes
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
        "shape": list(output.shape),
        "element_count": output.size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "grad_input_buffer_reused":
            buffer_reused,
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(
                BACKWARD_SOURCE
            ),
    }

    return grad_input, metadata


def tanh_backward_device(
    runtime: TensionForgeRuntime,
    output: DeviceTensor,
    grad_output: DeviceTensor,
    *,
    grad_input: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    return _activation_backward_device(
        runtime,
        output,
        grad_output,
        kernel_name="tanh_backward_fp32",
        operation_name="tanh_backward_device_fp32",
        grad_input=grad_input,
        repetitions=repetitions,
    )


def sigmoid_backward_device(
    runtime: TensionForgeRuntime,
    output: DeviceTensor,
    grad_output: DeviceTensor,
    *,
    grad_input: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    return _activation_backward_device(
        runtime,
        output,
        grad_output,
        kernel_name="sigmoid_backward_fp32",
        operation_name="sigmoid_backward_device_fp32",
        grad_input=grad_input,
        repetitions=repetitions,
    )


def tension_update_backward_device(
    runtime: TensionForgeRuntime,
    state: DeviceTensor,
    proposal: DeviceTensor,
    gate: DeviceTensor,
    grad_output: DeviceTensor,
    *,
    grad_state: DeviceTensor | None = None,
    grad_proposal: DeviceTensor | None = None,
    grad_gate: DeviceTensor | None = None,
    repetitions: int = 1,
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

    for name, tensor in (
        ("state", state),
        ("proposal", proposal),
        ("gate", gate),
        ("grad_output", grad_output),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if not (
        state.shape
        == proposal.shape
        == gate.shape
        == grad_output.shape
    ):
        raise ValueError(
            "state, proposal, gate, and grad_output "
            "shapes must match"
        )

    reused = {
        "grad_state": grad_state is not None,
        "grad_proposal": grad_proposal is not None,
        "grad_gate": grad_gate is not None,
    }

    if grad_state is None:
        grad_state = DeviceTensor.empty(
            runtime,
            state.shape,
            dtype=np.float32,
        )

    if grad_proposal is None:
        grad_proposal = DeviceTensor.empty(
            runtime,
            state.shape,
            dtype=np.float32,
        )

    if grad_gate is None:
        grad_gate = DeviceTensor.empty(
            runtime,
            state.shape,
            dtype=np.float32,
        )

    for name, tensor in (
        ("grad_state", grad_state),
        ("grad_proposal", grad_proposal),
        ("grad_gate", grad_gate),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

        if tensor.shape != state.shape:
            raise ValueError(
                f"{name} shape must match state"
            )

    kernel = runtime.kernel(
        BACKWARD_SOURCE,
        "tension_update_backward_fp32",
    )

    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        state.size,
        local_size,
    )

    arguments = (
        state.buffer,
        proposal.buffer,
        gate.buffer,
        grad_output.buffer,
        grad_state.buffer,
        grad_proposal.buffer,
        grad_gate.buffer,
        np.uint32(state.size),
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
        state.nbytes
        + proposal.nbytes
        + gate.nbytes
        + grad_output.nbytes
        + grad_state.nbytes
        + grad_proposal.nbytes
        + grad_gate.nbytes
    )

    bandwidth_gbps = (
        bytes_processed
        / (median_ms * 1e-3)
        / 1e9
        if median_ms is not None
        else None
    )

    metadata: dict[str, Any] = {
        "operation":
            "tension_update_backward_device_fp32",
        "shape": list(state.shape),
        "element_count": state.size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "buffers_reused": reused,
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(
                BACKWARD_SOURCE
            ),
    }

    return (
        grad_state,
        grad_proposal,
        grad_gate,
        metadata,
    )
