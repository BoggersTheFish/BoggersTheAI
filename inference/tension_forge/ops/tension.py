from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


TENSION_UPDATE_SOURCE = r"""
__kernel void tension_update_fp32(
    __global const float *state,
    __global const float *proposal,
    __global const float *gate,
    __global float *output,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float current_state = state[index];
        const float proposed_state = proposal[index];
        const float tension = gate[index];

        output[index] =
            current_state
            + tension
            * (
                proposed_state
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


def tension_update_device(
    runtime: TensionForgeRuntime,
    state: DeviceTensor,
    proposal: DeviceTensor,
    gate: DeviceTensor,
    *,
    output: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[DeviceTensor, dict[str, Any]]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    for name, tensor in (
        ("state", state),
        ("proposal", proposal),
        ("gate", gate),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if proposal.shape != state.shape:
        raise ValueError(
            "proposal shape must match state shape. "
            f"State {state.shape}, "
            f"proposal {proposal.shape}"
        )

    if gate.shape != state.shape:
        raise ValueError(
            "gate shape must match state shape. "
            f"State {state.shape}, gate {gate.shape}"
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
                "output shape must match state shape. "
                f"Expected {state.shape}, "
                f"received {output.shape}"
            )

    kernel = runtime.kernel(
        TENSION_UPDATE_SOURCE,
        "tension_update_fp32",
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
        output.buffer,
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
        "operation":
            "tension_update_device_fp32",
        "shape": list(state.shape),
        "element_count": state.size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "output_buffer_reused":
            output_was_reused,
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(
                TENSION_UPDATE_SOURCE
            ),
    }

    return output, metadata
