# Mega PRIME — Native Cortex V1

Status:

    FROZEN DEVELOPMENT ARCHITECTURE

Purpose:

    Build the first serious PRIME-native low-compute language cortex.

The design combines:

    efficient learned tokenization;
    multi-timescale recurrent fast memory;
    exact bounded local attention;
    sparse expert computation;
    low-bit effective projections;
    predictive latent learning;
    native observability.

The cortex remains epistemically non-authoritative.

---

# Model

Vocabulary:

    4096 BPE tokens

Model width:

    192

Layers:

    4

Recurrent memory heads:

    6

Approximate recurrent half-life priors:

    4 tokens
    12 tokens
    32 tokens
    96 tokens
    256 tokens
    768 tokens

Sparse experts per layer:

    6

Expert hidden dimension:

    384

Training routing:

    top-2

Inference routing:

    top-1

Local attention:

    every second layer

Local attention window:

    64 tokens

Attention heads:

    6

Vocabulary decoder:

    factorized

    192
      -> 64
      -> 4096

This avoids a dense 192 x 4096 output projection.

---

# Learning objectives

Primary:

    causal next-token prediction

Auxiliary:

    future latent-state prediction

Router objectives:

    load balancing;
    router logit regularization;
    entropy encouragement.

Router regularization is stronger early in training and anneals as the cortex
develops.

---

# Memory

Each recurrent head has a different prior retention timescale.

Dynamic erase and write gates modulate those priors.

The architecture is intended to support simultaneous:

    short linguistic state;
    clause-scale state;
    discourse-scale state;
    long-lived contextual state.

---

# Observability

Development evaluation records:

    expert usage;
    routing entropy;
    routing confidence;
    recurrent-state norm;
    erase strength;
    write strength;
    retention strength;
    local-attention entropy.

---

# Mandatory ablations

NORMAL

    full architecture

RESET_RECURRENCE

    recurrent matrix state is erased each token;
    local attention remains available

NO_LOCAL_ATTENTION

    recurrent state remains;
    exact local-attention workspace is disabled

These distinguish the utility of the two memory mechanisms.

---

# Authority

The Native Cortex may propose.

It may not:

    authorize knowledge;
    write canonical PRIME state;
    mutate receipts;
    declare generated language true.

Cortex authority is always:

    NONE

---

# Dataset boundary

TRAIN:

    permitted for fitting

DEVELOPMENT:

    permitted for architecture analysis

HELDOUT:

    forbidden during V1 development

Held-out evaluation requires a separately frozen evaluator after V1
architecture development is complete.
