from __future__ import annotations

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


WORKSPACE_OPS_SOURCE = r"""
__kernel void workspace_reduce_fp32(
    __global const float *input, __global float *mean,
    __global float *maximum, const uint batches, const uint slots,
    const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * features) return;
    const uint batch = index / features;
    const uint feature = index % features;
    float total = 0.0f;
    float largest = -INFINITY;
    for (uint slot = 0; slot < slots; ++slot) {
        const float value = input[(batch * slots + slot) * features + feature];
        total += value;
        largest = fmax(largest, value);
    }
    mean[index] = total / (float)slots;
    maximum[index] = largest;
}

__kernel void layer_norm_fp32(
    __global const float *input, __global const float *weight,
    __global const float *bias, __global float *output,
    const uint rows, const uint columns, const float epsilon
) {
    const uint row = get_global_id(0);
    if (row >= rows) return;
    const uint offset = row * columns;
    float mean = 0.0f;
    for (uint col = 0; col < columns; ++col) mean += input[offset + col];
    mean /= (float)columns;
    float variance = 0.0f;
    for (uint col = 0; col < columns; ++col) {
        const float delta = input[offset + col] - mean;
        variance += delta * delta;
    }
    variance /= (float)columns;
    const float inverse = rsqrt(variance + epsilon);
    for (uint col = 0; col < columns; ++col) {
        output[offset + col] = (input[offset + col] - mean) * inverse
            * weight[col] + bias[col];
    }
}

__kernel void softmax_rows_fp32(
    __global const float *input, __global float *output,
    const uint rows, const uint columns
) {
    const uint row = get_global_id(0);
    if (row >= rows) return;
    const uint offset = row * columns;
    float largest = -INFINITY;
    for (uint col = 0; col < columns; ++col) largest = fmax(largest, input[offset + col]);
    float total = 0.0f;
    for (uint col = 0; col < columns; ++col) total += exp(input[offset + col] - largest);
    for (uint col = 0; col < columns; ++col) output[offset + col] = exp(input[offset + col] - largest) / total;
}

__kernel void topk_rows_fp32(
    __global const float *input, __global float *values,
    __global int *indices, const uint rows, const uint columns, const uint k
) {
    const uint row = get_global_id(0);
    if (row >= rows) return;
    for (uint rank = 0; rank < k; ++rank) {
        float best = -INFINITY;
        int best_index = -1;
        for (uint col = 0; col < columns; ++col) {
            int used = 0;
            for (uint prior = 0; prior < rank; ++prior)
                used |= indices[row * k + prior] == (int)col;
            const float candidate = input[row * columns + col];
            if (!used && (candidate > best || (candidate == best && (best_index < 0 || (int)col < best_index)))) {
                best = candidate;
                best_index = (int)col;
            }
        }
        values[row * k + rank] = best;
        indices[row * k + rank] = best_index;
    }
}

__kernel void gather_batched_fp32(
    __global const float *input, __global const int *indices,
    __global float *output, const uint batches, const uint slots,
    const uint selected, const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * selected * features) return;
    const uint feature = index % features;
    const uint item = index / features;
    const uint pick = item % selected;
    const uint batch = item / selected;
    const uint slot = (uint)indices[batch * selected + pick];
    output[index] = input[(batch * slots + slot) * features + feature];
}

__kernel void gather_shared_fp32(
    __global const float *input, __global const int *indices,
    __global float *output, const uint batches, const uint slots,
    const uint selected, const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * selected * features) return;
    const uint feature = index % features;
    const uint item = index / features;
    const uint pick = item % selected;
    const uint batch = item / selected;
    const uint slot = (uint)indices[batch * selected + pick];
    output[index] = input[slot * features + feature];
}

__kernel void scatter_batched_fp32(
    __global const float *input, __global const int *indices,
    __global const float *updates, __global float *output,
    const uint batches, const uint slots, const uint selected, const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * slots * features) return;
    const uint feature = index % features;
    const uint item = index / features;
    const uint slot = item % slots;
    const uint batch = item / slots;
    float value = input[index];
    for (uint pick = 0; pick < selected; ++pick) {
        if ((uint)indices[batch * selected + pick] == slot)
            value = updates[(batch * selected + pick) * features + feature];
    }
    output[index] = value;
}

__kernel void concatenate_columns_fp32(
    __global const float *left, __global const float *right,
    __global float *output, const uint rows, const uint left_columns,
    const uint right_columns
) {
    const uint index = get_global_id(0);
    const uint columns = left_columns + right_columns;
    if (index >= rows * columns) return;
    const uint row = index / columns;
    const uint col = index % columns;
    output[index] = col < left_columns
        ? left[row * left_columns + col]
        : right[row * right_columns + col - left_columns];
}

__kernel void broadcast_rows_fp32(
    __global const float *input, __global float *output,
    const uint batches, const uint repeats, const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * repeats * features) return;
    const uint feature = index % features;
    const uint batch = index / (repeats * features);
    output[index] = input[batch * features + feature];
}

__kernel void broadcast_table_row_fp32(
    __global const float *table, __global float *output,
    const uint rows, const uint features, const uint table_row
) {
    const uint index = get_global_id(0);
    if (index < rows * features) output[index] = table[table_row * features + index % features];
}

__kernel void gelu_fp32(
    __global const float *input, __global float *output, const uint count
) {
    const uint index = get_global_id(0);
    if (index < count) {
        const float x = input[index];
        output[index] = 0.5f * x * (1.0f + erf(x * 0.7071067811865475f));
    }
}

__kernel void scale_fp32(
    __global const float *input, __global float *output,
    const float scale, const uint count
) {
    const uint index = get_global_id(0);
    if (index < count) output[index] = input[index] * scale;
}

__kernel void row_delta_norm_fp32(
    __global const float *left, __global const float *right,
    __global float *output, const uint rows, const uint columns
) {
    const uint row = get_global_id(0);
    if (row >= rows) return;
    float total = 0.0f;
    for (uint col = 0; col < columns; ++col) {
        const float delta = left[row * columns + col] - right[row * columns + col];
        total += delta * delta;
    }
    output[row] = sqrt(total);
}

__kernel void tension_update_broadcast_fp32(
    __global const float *state, __global const float *proposal,
    __global const float *gate, __global float *output,
    const uint rows, const uint columns
) {
    const uint index = get_global_id(0);
    if (index < rows * columns) {
        const float current = state[index];
        output[index] = current + gate[index / columns] * (proposal[index] - current);
    }
}

__kernel void batched_dot_fp32(
    __global const float *query, __global const float *slots,
    __global float *output, const uint batches, const uint count,
    const uint features, const float scale
) {
    const uint index = get_global_id(0);
    if (index >= batches * count) return;
    const uint batch = index / count;
    float total = 0.0f;
    for (uint feature = 0; feature < features; ++feature)
        total += query[batch * features + feature] * slots[index * features + feature];
    output[index] = total * scale;
}

__kernel void add_tension_penalty_fp32(
    __global const float *scores, __global const float *tension,
    __global float *output, const uint count
) {
    const uint index = get_global_id(0);
    if (index < count) {
        const float clipped = clamp(tension[index], 0.0f, 0.999f);
        output[index] = scores[index] + log1p(-clipped);
    }
}

__kernel void weighted_sum_fp32(
    __global const float *weights, __global const float *values,
    __global float *output, const uint batches, const uint count,
    const uint features
) {
    const uint index = get_global_id(0);
    if (index >= batches * features) return;
    const uint batch = index / features;
    const uint feature = index % features;
    float total = 0.0f;
    for (uint item = 0; item < count; ++item)
        total += weights[batch * count + item] * values[(batch * count + item) * features + feature];
    output[index] = total;
}
"""


def _check(runtime: TensionForgeRuntime, tensor: DeviceTensor, name: str, *, dtype=np.float32) -> None:
    if tensor.runtime is not runtime:
        raise ValueError(f"{name} belongs to a different runtime")
    if tensor.dtype != np.dtype(dtype):
        raise ValueError(f"{name} must use {np.dtype(dtype)}, received {tensor.dtype}")


def _output(runtime, shape, output, *, dtype=np.float32):
    if output is None:
        return DeviceTensor.empty(runtime, shape, dtype=dtype)
    _check(runtime, output, "output", dtype=dtype)
    if output.shape != shape:
        raise ValueError(f"output must have shape {shape}, received {output.shape}")
    return output


def _run(runtime, name, count, arguments):
    local = min(256, int(runtime.device.max_work_group_size))
    kernel = runtime.kernel(WORKSPACE_OPS_SOURCE, name)
    runtime.run_kernel(kernel, global_size=(runtime.round_up(count, local),), local_size=(local,), arguments=arguments)


def workspace_reduce_device(runtime, workspace, *, mean=None, maximum=None):
    _check(runtime, workspace, "workspace")
    if workspace.ndim != 3:
        raise ValueError("workspace must have shape [batch, slots, features]")
    batches, slots, features = workspace.shape
    mean = _output(runtime, (batches, features), mean)
    maximum = _output(runtime, (batches, features), maximum)
    _run(runtime, "workspace_reduce_fp32", batches * features, (workspace.buffer, mean.buffer, maximum.buffer, np.uint32(batches), np.uint32(slots), np.uint32(features)))
    return mean, maximum


def layer_norm_device(runtime, inputs, weight, bias, *, epsilon=1e-5, output=None):
    for name, tensor in (("inputs", inputs), ("weight", weight), ("bias", bias)):
        _check(runtime, tensor, name)
    if inputs.ndim < 2 or weight.shape != (inputs.shape[-1],) or bias.shape != weight.shape:
        raise ValueError("LayerNorm shapes are incompatible")
    rows, columns = inputs.size // inputs.shape[-1], inputs.shape[-1]
    output = _output(runtime, inputs.shape, output)
    _run(runtime, "layer_norm_fp32", rows, (inputs.buffer, weight.buffer, bias.buffer, output.buffer, np.uint32(rows), np.uint32(columns), np.float32(epsilon)))
    return output


def softmax_device(runtime, inputs, *, output=None):
    _check(runtime, inputs, "inputs")
    if inputs.ndim < 2:
        raise ValueError("inputs must have at least two dimensions")
    rows, columns = inputs.size // inputs.shape[-1], inputs.shape[-1]
    output = _output(runtime, inputs.shape, output)
    _run(runtime, "softmax_rows_fp32", rows, (inputs.buffer, output.buffer, np.uint32(rows), np.uint32(columns)))
    return output


def topk_device(runtime, inputs, k, *, values=None, indices=None):
    _check(runtime, inputs, "inputs")
    if inputs.ndim != 2 or not 1 <= k <= inputs.shape[1]:
        raise ValueError("top-k expects [rows, columns] and k in range")
    rows, columns = inputs.shape
    values = _output(runtime, (rows, k), values)
    indices = _output(runtime, (rows, k), indices, dtype=np.int32)
    _run(runtime, "topk_rows_fp32", rows, (inputs.buffer, values.buffer, indices.buffer, np.uint32(rows), np.uint32(columns), np.uint32(k)))
    return values, indices


def gather_slots_device(runtime, inputs, indices, *, shared=False, output=None):
    _check(runtime, inputs, "inputs")
    _check(runtime, indices, "indices", dtype=np.int32)
    if indices.ndim != 2 or inputs.ndim not in (2, 3):
        raise ValueError("gather expects indices [batch, selected] and rank-2/3 inputs")
    batches, selected = indices.shape
    if shared:
        if inputs.ndim != 2:
            raise ValueError("shared gather input must have shape [slots, features]")
        slots, features = inputs.shape
    else:
        if inputs.ndim != 3 or inputs.shape[0] != batches:
            raise ValueError("batched gather input must have shape [batch, slots, features]")
        _, slots, features = inputs.shape
    output = _output(runtime, (batches, selected, features), output)
    kernel = "gather_shared_fp32" if shared else "gather_batched_fp32"
    _run(runtime, kernel, output.size, (inputs.buffer, indices.buffer, output.buffer, np.uint32(batches), np.uint32(slots), np.uint32(selected), np.uint32(features)))
    return output


def scatter_slots_device(runtime, inputs, indices, updates, *, output=None):
    for name, tensor in (("inputs", inputs), ("updates", updates)):
        _check(runtime, tensor, name)
    _check(runtime, indices, "indices", dtype=np.int32)
    if inputs.ndim != 3 or indices.ndim != 2 or updates.ndim != 3:
        raise ValueError("scatter expects rank-3 input/update and rank-2 indices")
    batches, slots, features = inputs.shape
    selected = indices.shape[1]
    if indices.shape[0] != batches or updates.shape != (batches, selected, features):
        raise ValueError("scatter shapes are incompatible")
    output = _output(runtime, inputs.shape, output)
    _run(runtime, "scatter_batched_fp32", output.size, (inputs.buffer, indices.buffer, updates.buffer, output.buffer, np.uint32(batches), np.uint32(slots), np.uint32(selected), np.uint32(features)))
    return output


def concatenate_columns_device(runtime, left, right, *, output=None):
    _check(runtime, left, "left"); _check(runtime, right, "right")
    if left.ndim != 2 or right.ndim != 2 or left.shape[0] != right.shape[0]:
        raise ValueError("concatenation expects rank-2 tensors with equal rows")
    rows, lc = left.shape; rc = right.shape[1]
    output = _output(runtime, (rows, lc + rc), output)
    _run(runtime, "concatenate_columns_fp32", output.size, (left.buffer, right.buffer, output.buffer, np.uint32(rows), np.uint32(lc), np.uint32(rc)))
    return output


def broadcast_rows_device(runtime, inputs, repeats, *, output=None):
    _check(runtime, inputs, "inputs")
    if inputs.ndim != 2 or repeats < 1:
        raise ValueError("broadcast expects rank-2 input and positive repeats")
    batches, features = inputs.shape
    output = _output(runtime, (batches * repeats, features), output)
    _run(runtime, "broadcast_rows_fp32", output.size, (inputs.buffer, output.buffer, np.uint32(batches), np.uint32(repeats), np.uint32(features)))
    return output


def broadcast_table_row_device(runtime, table, row, output_rows, *, output=None):
    _check(runtime, table, "table")
    if table.ndim != 2 or not 0 <= row < table.shape[0] or output_rows < 1:
        raise ValueError("invalid table broadcast")
    features = table.shape[1]
    output = _output(runtime, (output_rows, features), output)
    _run(runtime, "broadcast_table_row_fp32", output.size, (table.buffer, output.buffer, np.uint32(output_rows), np.uint32(features), np.uint32(row)))
    return output


def gelu_device(runtime, inputs, *, output=None):
    _check(runtime, inputs, "inputs"); output = _output(runtime, inputs.shape, output)
    _run(runtime, "gelu_fp32", inputs.size, (inputs.buffer, output.buffer, np.uint32(inputs.size)))
    return output


def scale_device(runtime, inputs, scale, *, output=None):
    _check(runtime, inputs, "inputs"); output = _output(runtime, inputs.shape, output)
    _run(runtime, "scale_fp32", inputs.size, (inputs.buffer, output.buffer, np.float32(scale), np.uint32(inputs.size)))
    return output


def row_delta_norm_device(runtime, left, right, *, output=None):
    _check(runtime, left, "left"); _check(runtime, right, "right")
    if left.ndim != 2 or right.shape != left.shape:
        raise ValueError("row norm inputs must be equal rank-2 tensors")
    rows, columns = left.shape; output = _output(runtime, (rows, 1), output)
    _run(runtime, "row_delta_norm_fp32", rows, (left.buffer, right.buffer, output.buffer, np.uint32(rows), np.uint32(columns)))
    return output


def tension_update_broadcast_device(runtime, state, proposal, gate, *, output=None):
    _check(runtime, state, "state"); _check(runtime, proposal, "proposal"); _check(runtime, gate, "gate")
    if state.ndim != 2 or proposal.shape != state.shape or gate.shape != (state.shape[0], 1):
        raise ValueError("broadcast tension update shapes are incompatible")
    rows, columns = state.shape; output = _output(runtime, state.shape, output)
    _run(runtime, "tension_update_broadcast_fp32", state.size, (state.buffer, proposal.buffer, gate.buffer, output.buffer, np.uint32(rows), np.uint32(columns)))
    return output


def batched_dot_device(runtime, query, slots, *, scale=1.0, output=None):
    _check(runtime, query, "query"); _check(runtime, slots, "slots")
    if query.ndim != 2 or slots.ndim != 3 or query.shape[0] != slots.shape[0] or query.shape[1] != slots.shape[2]:
        raise ValueError("batched dot shapes are incompatible")
    batches, count, features = slots.shape; output = _output(runtime, (batches, count), output)
    _run(runtime, "batched_dot_fp32", output.size, (query.buffer, slots.buffer, output.buffer, np.uint32(batches), np.uint32(count), np.uint32(features), np.float32(scale)))
    return output


def add_tension_penalty_device(runtime, scores, tension, *, output=None):
    _check(runtime, scores, "scores"); _check(runtime, tension, "tension")
    if tension.size != scores.size:
        raise ValueError("scores and tension must have equal element counts")
    output = _output(runtime, scores.shape, output)
    _run(runtime, "add_tension_penalty_fp32", scores.size, (scores.buffer, tension.buffer, output.buffer, np.uint32(scores.size)))
    return output


def weighted_sum_device(runtime, weights, values, *, output=None):
    _check(runtime, weights, "weights"); _check(runtime, values, "values")
    if weights.ndim != 2 or values.ndim != 3 or weights.shape != values.shape[:2]:
        raise ValueError("weighted sum shapes are incompatible")
    batches, count = weights.shape; features = values.shape[2]
    output = _output(runtime, (batches, features), output)
    _run(runtime, "weighted_sum_fp32", output.size, (weights.buffer, values.buffer, output.buffer, np.uint32(batches), np.uint32(count), np.uint32(features)))
    return output
