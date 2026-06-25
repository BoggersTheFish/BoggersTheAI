from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


MSE_SOURCE = r"""
__kernel void mse_loss_grad_fp32(
    __global const float *prediction,
    __global const float *target,
    __global float *loss_terms,
    __global float *grad_prediction,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float difference =
            prediction[index] - target[index];

        const float inverse_count =
            1.0f / (float)count;

        loss_terms[index] =
            difference
            * difference
            * inverse_count;

        grad_prediction[index] =
            2.0f
            * difference
            * inverse_count;
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


def mse_loss_grad_device(
    runtime: TensionForgeRuntime,
    prediction: DeviceTensor,
    target: DeviceTensor,
    *,
    loss_terms: DeviceTensor | None = None,
    grad_prediction: DeviceTensor | None = None,
    repetitions: int = 1,
) -> tuple[
    DeviceTensor,
    DeviceTensor,
    dict[str, Any],
]:
    if repetitions < 1:
        raise ValueError(
            "repetitions must be at least one"
        )

    _validate_tensor(
        runtime,
        prediction,
        "prediction",
    )

    _validate_tensor(
        runtime,
        target,
        "target",
    )

    if prediction.shape != target.shape:
        raise ValueError(
            "prediction and target shapes must "
            "match. "
            f"Prediction {prediction.shape}, "
            f"target {target.shape}"
        )

    loss_terms_reused = loss_terms is not None
    grad_prediction_reused = (
        grad_prediction is not None
    )

    if loss_terms is None:
        loss_terms = DeviceTensor.empty(
            runtime,
            prediction.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            loss_terms,
            "loss_terms",
        )

        if loss_terms.shape != prediction.shape:
            raise ValueError(
                "loss_terms shape must match "
                "prediction"
            )

    if grad_prediction is None:
        grad_prediction = DeviceTensor.empty(
            runtime,
            prediction.shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor(
            runtime,
            grad_prediction,
            "grad_prediction",
        )

        if (
            grad_prediction.shape
            != prediction.shape
        ):
            raise ValueError(
                "grad_prediction shape must match "
                "prediction"
            )

    kernel = runtime.kernel(
        MSE_SOURCE,
        "mse_loss_grad_fp32",
    )

    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        prediction.size,
        local_size,
    )

    arguments = (
        prediction.buffer,
        target.buffer,
        loss_terms.buffer,
        grad_prediction.buffer,
        np.uint32(prediction.size),
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
        prediction.nbytes
        + target.nbytes
        + loss_terms.nbytes
        + grad_prediction.nbytes
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
            "mse_loss_grad_device_fp32",
        "shape": list(prediction.shape),
        "element_count": prediction.size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "approximate_bandwidth_gbps":
            bandwidth_gbps,
        "buffers_reused": {
            "loss_terms":
                loss_terms_reused,
            "grad_prediction":
                grad_prediction_reused,
        },
        "host_transfers_during_repetitions": 0,
        "source_sha256":
            runtime.source_hash(MSE_SOURCE),
    }

    return (
        loss_terms,
        grad_prediction,
        metadata,
    )
