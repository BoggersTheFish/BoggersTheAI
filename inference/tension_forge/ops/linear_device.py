from __future__ import annotations

from typing import Any

import numpy as np

from tensionforge.ops.linear import LINEAR_SOURCE
from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


def _validate_tensor_runtime(
    runtime: TensionForgeRuntime,
    tensor: DeviceTensor,
    name: str,
) -> None:
    if tensor.runtime is not runtime:
        raise ValueError(
            f"{name} belongs to a different runtime"
        )


def _require_fp32(
    tensor: DeviceTensor,
    name: str,
) -> None:
    if tensor.dtype != np.dtype(np.float32):
        raise ValueError(
            f"{name} must use float32, received "
            f"{tensor.dtype}"
        )


def linear_device(
    runtime: TensionForgeRuntime,
    inputs: DeviceTensor,
    weights: DeviceTensor,
    bias: DeviceTensor,
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

    for name, tensor in (
        ("inputs", inputs),
        ("weights", weights),
        ("bias", bias),
    ):
        _validate_tensor_runtime(
            runtime,
            tensor,
            name,
        )

        _require_fp32(
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
            "Bias shape must match output features. "
            f"Expected {(output_features,)}, "
            f"received {bias.shape}"
        )

    expected_output_shape = (
        batch_size,
        output_features,
    )

    if output is None:
        output = DeviceTensor.empty(
            runtime,
            expected_output_shape,
            dtype=np.float32,
        )
    else:
        _validate_tensor_runtime(
            runtime,
            output,
            "output",
        )

        _require_fp32(
            output,
            "output",
        )

        if output.shape != expected_output_shape:
            raise ValueError(
                "Output shape is incorrect. "
                f"Expected {expected_output_shape}, "
                f"received {output.shape}"
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
        inputs.buffer,
        weights.buffer,
        bias.buffer,
        output.buffer,
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
        "operation":
            "linear_forward_device_fp32",
        "input_shape": list(inputs.shape),
        "weight_shape": list(weights.shape),
        "bias_shape": list(bias.shape),
        "output_shape": list(output.shape),
        "tile_size": tile_size,
        "repetitions": repetitions,
        "median_kernel_ms": median_ms,
        "gflops": gflops,
        "host_transfers_during_repetitions": 0,
        "output_buffer_reused":
            output is not None,
        "source_sha256":
            runtime.source_hash(LINEAR_SOURCE),
        "compile_options":
            list(compile_options),
    }

    return output, metadata
