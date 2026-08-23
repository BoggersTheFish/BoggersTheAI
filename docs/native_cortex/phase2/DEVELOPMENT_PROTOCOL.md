# Mega PRIME Native Cortex — Phase II

## Purpose

Test whether the Native Cortex can acquire reusable natural-language
competence efficiently from heterogeneous real prose.

This phase evaluates:

- unseen-language generalisation;
- token efficiency;
- recurrent-memory utility;
- expert-routing health;
- recurrent-state health;
- parameter efficiency;
- training throughput.

## Dataset isolation

Documents are assigned by SHA-256 content hash.

TRAIN:
    may be used for model fitting and tokenizer training.

DEVELOPMENT:
    may be evaluated during architecture development.

HELDOUT:
    must not be inspected, decoded, sampled, trained upon, or used for
    architecture selection before the final evaluator and architecture are
    separately frozen.

Metadata such as document count, byte count and cryptographic hashes may be
recorded without revealing held-out content.

## Primary development measurements

- training cross entropy;
- development cross entropy;
- development perplexity;
- bits per UTF-8 byte;
- training tokens per second;
- parameter count.

## Recurrent-memory diagnostic

Compare:

    NORMAL
        recurrent state persists between tokens;

    RESET
        recurrent state is reset every token.

Retained recurrence only earns architectural credit when it improves unseen
development prediction.

## Sparse-expert diagnostic

Measure:

- utilization by expert;
- routing entropy;
- maximum expert share;
- routing confidence.

A falling loss alone does not establish healthy expert specialization.

## Recurrent-state diagnostic

Measure:

- state norms;
- read norms;
- erase strength;
- write strength;
- state growth over sequence length.

## Authority

Native Cortex authority is always:

    NONE

Generated language and neural proposals are not canonical PRIME knowledge.

## Heldout

This document does not authorize held-out evaluation.
