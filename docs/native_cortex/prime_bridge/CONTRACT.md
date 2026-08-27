# Mega PRIME — Cortex ↔ PRIME Bridge Contract

## Purpose

Connect the learned Native Cortex to the canonical verifier-first PRIME
substrate without transferring epistemic authority to the neural model.

## Direction A — Language to PRIME

raw text
    -> cortex representation
    -> semantic proposal
    -> proposed TS structure
    -> PRIME verifier
    -> verdict / repair / abstention
    -> receipt

Cortex proposals use:

    provenance = model_proposer
    status     = proposed

A neural proposal is never canonical by construction.

## Direction B — PRIME to Cortex

verifier outcome
    -> labelled neural experience
    -> verifier-prediction learning
    -> representation repair learning

The cortex may learn to predict PRIME's future decision.

Prediction of authority is not authority.

## Bootstrap semantics

During initial bridge development the existing deterministic TSLC compiler
acts as a semantic teacher.

The cortex learns:

    text -> TSLC-style semantic proposal

This is distillation of representation, not epistemic truth.

The compiled proposal is independently passed to PRIME verification.

## Verifier labels

UNKNOWN
ACCEPT
REJECT
REPAIR
ABSTAIN

## Provenance

Every bridge training record contains:

    source hash
    semantic proposal hash
    verifier result
    verifier-result hash
    parent experience hash
    deterministic experience hash

The experience ledger is append-only and hash chained.

## Failure policy

Invalid neural semantic output:

    does not reach canonical mutation
    is recorded as failed proposal
    authority remains NONE

Verifier exception:

    produces UNKNOWN
    does not become ACCEPT

## Dataset isolation

TRAIN may produce bridge training records.

DEVELOPMENT may produce evaluation records.

HELDOUT remains forbidden.

## Canonical rule

    suggestion != authority

The component that learns from verifier decisions is not the component that
makes those decisions.
