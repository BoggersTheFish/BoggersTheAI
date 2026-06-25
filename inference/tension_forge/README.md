# TensionForge

A small verifier-first GPU training runtime built for legacy commodity hardware.

## Current hardware

- AMD Radeon RX 480 Gaming X
- 8 GiB VRAM
- Mesa Rusticl OpenCL backend
- Linux Mint
- No ROCm or CUDA dependency

## Verified milestones

### M0 — GPU execution

A handwritten OpenCL SAXPY kernel ran on the RX 480 and matched the CPU
reference with zero error.

Measured device-memory bandwidth:

- approximately 196 GB/s

### M1 — Matrix multiplication

A handwritten tiled FP32 matrix multiplication kernel reached approximately:

- 921 GFLOPS for a 1024 x 1024 matrix

All tested outputs matched NumPy within declared tolerances.

### M2 — GPU training

A complete linear model was trained using custom OpenCL kernels for:

- forward propagation
- prediction error
- weight gradients
- bias gradients
- input gradients
- SGD parameter updates

Results:

- initial loss: 38.4889106750
- final loss: effectively zero
- training steps: 200
- training time: approximately 0.597 seconds
- maximum weight recovery error: approximately 5.96e-7
- all GPU operations verified against NumPy

## Goal

Develop a narrow training runtime for TensionLM that uses:

- persistent GPU tensors
- CPU reference verification
- fixed-shape compiled kernels
- fused tension operations
- tension-gated compute allocation
- deterministic JSON receipts

## TensionForge v0.2 runtime foundation

TensionForge is being converted from standalone experiments into a reusable
OpenCL runtime.

The initial runtime foundation provides:

- central RX 480 and Rusticl device discovery;
- reusable OpenCL context and profiling queue;
- compiled program and kernel caching;
- checked GPU buffer allocation;
- CPU-to-GPU and GPU-to-CPU transfer helpers;
- reusable operation modules;
- deterministic JSON verification receipts.

The first migrated operation is FP32 SAXPY. It is available through the public
`TensionForgeRuntime` and `tensionforge.ops` APIs rather than embedding a full
runtime inside the experiment.

## Reusable tiled matrix multiplication

The verified tiled FP32 matrix multiplication kernel has been migrated into
the public TensionForge runtime.

The operation now provides:

- arbitrary two-dimensional matrix shapes;
- padded work-group dispatch for non-multiple dimensions;
- reusable OpenCL program and kernel caching;
- device work-group validation;
- profiling and calculated GFLOPS;
- NumPy parity tests;
- deterministic benchmark receipts.

## Fused linear forward operation

TensionForge provides a reusable fused FP32 linear operation:

    output = input @ weights + bias

Matrix multiplication and bias addition execute in one OpenCL kernel. This
reduces kernel launches and avoids a separate bias-addition pass.

The operation supports arbitrary batch, input-feature, and output-feature
dimensions, with NumPy parity tests, kernel profiling, compiled-kernel caching,
and deterministic benchmark receipts.

## Device-resident tensors

TensionForge now includes a DeviceTensor abstraction for persistent OpenCL
buffers.

DeviceTensor records shape, dtype, element count, byte size, runtime ownership,
and its underlying GPU buffer. Tensors can be uploaded once, reused across many
kernel executions, updated in place, and copied back only when verification or
external access is required.

The device-resident linear operation accepts DeviceTensor inputs, weights,
biases, and optional reusable output storage. Repeated execution performs no
CPU-to-GPU or GPU-to-CPU transfers between kernel launches.

## Device-resident tension operations

TensionForge provides reusable device-resident FP32 tanh and sigmoid
activations, plus the causal tension update used by tension-based recurrent
state systems.

The update computes:

    next_state = state + gate * (proposal - state)

Inputs and reusable outputs remain in GPU memory across repeated kernel
launches. NumPy references verify every operation, while receipts record
timings, approximate memory bandwidth, source hashes, and numerical errors.

## Fused tension pipeline

TensionForge includes a fused device-resident tension layer.

The kernel performs five logical operations in one launch:

    proposal = tanh(features @ proposal_weights + proposal_bias)
    gate = sigmoid(features @ gate_weights + gate_bias)
    next_state = state + gate * (proposal - state)

The unfused version requires two linear launches, two activation launches, and
one tension-update launch. The fused implementation reduces this from five
kernel launches to one while keeping features, weights, state, and output in
GPU memory.

NumPy and unfused-runtime references verify the fused output. Benchmark
receipts record numerical error, kernel timings, launch reduction, throughput,
and measured speedup.

## Device-resident linear backward

TensionForge provides reusable FP32 backward propagation for linear layers.

The runtime calculates:

    grad_input = grad_output @ weights transpose
    grad_weights = inputs transpose @ grad_output
    grad_bias = sum grad_output across the batch

Inputs, upstream gradients, parameter gradients, and optional reusable output
buffers remain in GPU memory. NumPy references verify all three gradients, and
receipts record individual kernel timings, combined throughput, source hashes,
buffer reuse, and numerical error.

## Composable device-resident training

TensionForge includes reusable device-resident mean-squared-error gradients and
an AdamW parameter update.

A complete training step can now be assembled from public runtime operations:

    prediction = linear(inputs, weights, bias)
    loss, grad_prediction = mse(prediction, target)
    grad_input, grad_weights, grad_bias = linear_backward(...)
    adamw(weights, grad_weights)
    adamw(bias, grad_bias)

Parameters, optimiser moments, activations, losses, and gradients remain in GPU
memory during training. Host transfers are only required when reading selected
metrics or verification results.

## Recurrent backward operations

TensionForge contains the backward operations required for recurrent tension
training.

The runtime calculates:

    tanh gradient = upstream * (1 - output squared)

    sigmoid gradient = upstream * output * (1 - output)

    state gradient = upstream * (1 - gate)
    proposal gradient = upstream * gate
    gate gradient = upstream * (proposal - state)

These operations provide the local derivatives required to perform full
backpropagation through time without moving recurrent states or gradients out
of GPU memory.

## Composable recurrent TensionCell

TensionForge includes a recurrent TensionCell assembled from reusable public
runtime operations.

Each recurrent step calculates:

    combined = concatenate(input, previous_state)
    proposal = tanh(linear(combined))
    gate = sigmoid(linear(combined))
    next_state = previous_state + gate * (proposal - previous_state)

The model retains every state, proposal, gate, and combined feature tensor in
GPU memory. Full backpropagation through time propagates the state gradient
backward through the sequence, accumulates recurrent parameter gradients, and
updates all parameters with device-resident AdamW.

A delayed-recall experiment verifies predictions and gradients against NumPy.
No experiment-specific monolithic training kernel is used.
# Ten-SON Bridge v0

TensionForge now has a forward-only bridge for the PyTorch Ten-SON `TensionWorkspace.forward_token` path. Token embeddings are supplied directly; tokenizer, vocabulary lookup, training, backward propagation, and generation are not ported.

The bridge keeps forward intermediates on the OpenCL device and matches workspace summaries, routing scores and probabilities, exact non-tied top-k indices, selected states, proposals, pre/post-update tension, updated and scattered workspaces, slot tension, readout weights, and the workspace-derived readout vector. The deterministic four-token parity run measured maximum absolute errors of `4.76837158e-07` for the development configuration and `6.55651093e-07` for the official CPU-validation dimensions. Both selected-index traces matched exactly; the final recurrent workspace errors were `7.4505806e-08` and `1.1920929e-07`, respectively, under `rtol=5e-4` and `atol=5e-4`.

Run the audit experiment with:

    .venv/bin/python experiments/ten_son_forward_parity.py

The next milestone is delayed-recall training parity. Bridge v0 performs no training or backward pass.

## Ten-SON Training Bridge v1

Bridge v0 established forward parity. Bridge v1 adds deterministic device-resident backward propagation through the workspace, recurrent sequence, token embedding, masked classifier loss, global gradient clipping, and one AdamW update.

The one-token and four-token controlled objectives match gradients for the trainable initial workspace, slot keys, summary normalization, router, proposal, tension, and readout groups, as well as supplied token embeddings. The real delayed-recall case additionally matches the embedding table and output classifier. Across Cases A, B, and C, the measured worst gradient maximum absolute error is `1.14440918e-05`, the worst non-negligible relative L2 error is `1.77889384e-05`, and the lowest non-negligible cosine similarity is `0.999999999846`. The single clipped AdamW update has a worst parameter maximum absolute error of `1.49011612e-07`.

Run the complete parity experiment with the required Rusticl driver selection:

    RUSTICL_ENABLE=radeonsi .venv/bin/python experiments/ten_son_training_step_parity.py

This result covers exactly one optimiser step; it is not long-run training parity. The next milestone is a short matched loss trajectory followed by CPU versus RX 480 timing.

## Ten-SON Training Bridge v2

Bridge v0 proved forward parity and v1 proved parameter-gradient and one-step AdamW parity. Bridge v2 extends the same implementation through 20 synchronized delayed-recall updates. All 21 pre/post-update rows passed, every selected-index trace matched, and the worst loss absolute error was `2.72365869e-07`. Checkpoint gradients, parameters, and AdamW first/second moments remained within their declared thresholds.

The steady-state development benchmark ran 50 steps per repetition. PyTorch CPU required a median `1.870282` seconds (`37.406` ms/step), while TensionForge on the RX 480 required `31.083813` seconds (`621.676` ms/step), a `0.060x` speedup ratio. Cold start was `0.843197` seconds for CPU and `0.912691` seconds for TensionForge.

The scientific-validation benchmark preserved the checked-in model dimensions, delayed-recall sequence length 20, and batch size 32, with 20 timed steps per repetition. PyTorch CPU required a median `2.589140` seconds (`129.457` ms/step), while TensionForge required `55.136640` seconds (`2756.832` ms/step), a `0.047x` ratio. Cold start was `0.151195` seconds for CPU and `2.403159` seconds for TensionForge.

By the milestone interpretation rule, TensionForge is currently slower than CPU and is not yet practically faster. Steady-state timing excludes construction, OpenCL compilation, parameter conversion/reset, batch generation/upload, receipt creation, diagnostic readbacks, and assertions. Five warm-up steps preceded timing, parameters and optimizer state were reset before every repetition, and timed GPU loops recorded zero host transfers. No kernel or runtime performance optimization was performed in v2.
