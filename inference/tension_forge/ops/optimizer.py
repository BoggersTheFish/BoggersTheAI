from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


ADAMW_SOURCE = r"""
__kernel void adamw_update_fp32(
    __global float *parameter,
    __global const float *gradient,
    __global float *first_moment,
    __global float *second_moment,
    const float learning_rate,
    const float beta1,
    const float beta2,
    const float one_minus_beta1,
    const float one_minus_beta2,
    const float inverse_bias_correction1,
    const float inverse_bias_correction2,
    const float epsilon,
    const float weight_decay,
    const unsigned int count
) {
    const unsigned int index = get_global_id(0);

    if (index < count) {
        const float gradient_value =
            gradient[index];

        const float first =
            beta1 * first_moment[index]
            + one_minus_beta1
            * gradient_value;

        const float second =
            beta2 * second_moment[index]
            + one_minus_beta2
            * gradient_value
            * gradient_value;

        first_moment[index] = first;
        second_moment[index] = second;

        const float corrected_first =
            first * inverse_bias_correction1;

        const float corrected_second =
            second * inverse_bias_correction2;

        const float decayed_parameter =
            parameter[index]
            * (
                1.0f
                - learning_rate
                * weight_decay
            );

        parameter[index] =
            decayed_parameter
            - learning_rate
            * corrected_first
            / (
                sqrt(corrected_second)
                + epsilon
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


def adamw_update_device(
    runtime: TensionForgeRuntime,
    parameter: DeviceTensor,
    gradient: DeviceTensor,
    first_moment: DeviceTensor,
    second_moment: DeviceTensor,
    *,
    step: int,
    learning_rate: float,
    beta1: float = 0.9,
    beta2: float = 0.999,
    epsilon: float = 1e-8,
    weight_decay: float = 0.0,
) -> dict[str, Any]:
    if step < 1:
        raise ValueError(
            "step must be at least one"
        )

    if learning_rate <= 0.0:
        raise ValueError(
            "learning_rate must be positive"
        )

    if not 0.0 <= beta1 < 1.0:
        raise ValueError(
            "beta1 must be in [0, 1)"
        )

    if not 0.0 <= beta2 < 1.0:
        raise ValueError(
            "beta2 must be in [0, 1)"
        )

    if epsilon <= 0.0:
        raise ValueError(
            "epsilon must be positive"
        )

    if weight_decay < 0.0:
        raise ValueError(
            "weight_decay cannot be negative"
        )

    for name, tensor in (
        ("parameter", parameter),
        ("gradient", gradient),
        ("first_moment", first_moment),
        ("second_moment", second_moment),
    ):
        _validate_tensor(
            runtime,
            tensor,
            name,
        )

    if gradient.shape != parameter.shape:
        raise ValueError(
            "gradient shape must match parameter"
        )

    if first_moment.shape != parameter.shape:
        raise ValueError(
            "first_moment shape must match "
            "parameter"
        )

    if second_moment.shape != parameter.shape:
        raise ValueError(
            "second_moment shape must match "
            "parameter"
        )

    inverse_bias_correction1 = (
        1.0
        / (
            1.0
            - beta1 ** step
        )
    )

    inverse_bias_correction2 = (
        1.0
        / (
            1.0
            - beta2 ** step
        )
    )

    kernel = runtime.kernel(
        ADAMW_SOURCE,
        "adamw_update_fp32",
    )

    local_size = min(
        256,
        int(runtime.device.max_work_group_size),
    )

    global_size = runtime.round_up(
        parameter.size,
        local_size,
    )

    elapsed_ms = runtime.run_kernel(
        kernel,
        global_size=(global_size,),
        local_size=(local_size,),
        arguments=(
            parameter.buffer,
            gradient.buffer,
            first_moment.buffer,
            second_moment.buffer,
            np.float32(learning_rate),
            np.float32(beta1),
            np.float32(beta2),
            np.float32(1.0 - beta1),
            np.float32(1.0 - beta2),
            np.float32(
                inverse_bias_correction1
            ),
            np.float32(
                inverse_bias_correction2
            ),
            np.float32(epsilon),
            np.float32(weight_decay),
            np.uint32(parameter.size),
        ),
    )

    return {
        "operation":
            "adamw_update_device_fp32",
        "shape": list(parameter.shape),
        "element_count": parameter.size,
        "step": step,
        "learning_rate":
            float(learning_rate),
        "beta1": float(beta1),
        "beta2": float(beta2),
        "epsilon": float(epsilon),
        "weight_decay":
            float(weight_decay),
        "kernel_ms": elapsed_ms,
        "host_transfers": 0,
        "source_sha256":
            runtime.source_hash(
                ADAMW_SOURCE
            ),
    }
