# Proof Against Token Prediction

TS-OS rejects the premise that thought is next-token prediction. This document
lays out the epistemological and mathematical arguments enforced by the system.

## The Softmax Trap

Standard transformers compute attention as:

```
attention[t, w] = softmax( dot(q_t, k_w) / √d )[w]
```

Every position competes for a fixed budget summing to 1. If one token pulls
harder, others pull less. This is **zero-sum** — a structural assumption that
truth is competitive rather than compositional.

## Tension as Alternative

TensionLM replaces softmax with independent sigmoid scores:

```
tau[t, w] = sigmoid( dot(q_t, k_w) / √d )
output[t] = Σ_w tau[t, w] * v_w
```

No competition. A token can be pulled hard by all neighbors simultaneously, or
barely pulled by any. The model learns which relationships matter without
forcing a zero-sum tradeoff.

## Graph-Wave as Alternative

BoggersTheAI maintains a **persistent living graph** where:

- Truth is the most stable constraint configuration, not the highest-probability token
- The wave cycle (Propagate → Relax → Prune → Evolve) runs continuously
- LLMs are synthesis tools invoked only when graph knowledge is insufficient
- Contradictions are first-class — they surface as tension, not suppressed logits

## Verifier-Gated Reasoning

TS-Reasoner enforces:

```
Confidence is not proof. Typed verifier support is the proof boundary.
```

Models propose candidates. Verifiers decide acceptance. Receipts record the
decision trail. No output is trusted without typed support.

## BOGVM-0 Determinism

The 16-opcode wave-state VM provides a deterministic bedrock:

- Same input → same state transition → same `.bogpk` artifact
- No stochastic sampling in the proof path
- Reconstruction is SHA-256 verified

## Implications for Researchers

1. Do not benchmark TS-OS on perplexity alone — measure verifier acceptance rates
2. Do not treat LLM outputs as ground truth — they are proposals
3. Do not skip `.bogpk` artifact trails — they are the reproducibility contract
4. Do not conflate activation with proof — check typed verifier support

## References

- TensionLM architecture: `inference/tension_lm/model.py`
- Wave cycle: `core/wave.py`, `core/graph/wave_runner.py`
- Verifier gates: `reasoner/ts_reasoner/cognitive_physics_engine.py`
- BOGVM opcodes: `core-vm/bogvm/opcodes.py`