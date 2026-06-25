# Anti-Token-Prediction — The Deconstruction

This document is the weapon.

If you have read [MANIFESTO.md](MANIFESTO.md), you already know the axiom:
thought is the stable configuration of constraints under wave propagation. This
document explains **why the dominant alternative — statistical next-token
prediction — cannot get you there**, and what TS-OS builds instead.

Read this before you touch the code. Read [truth-graph.md](truth-graph.md) after.

---

## I. The Softmax Illusion

Standard transformer attention computes:

```
attention[t, w] = softmax( dot(q_t, k_w) / √d )[w]
output[t]       = Σ_w attention[t, w] · v_w
```

The softmax is not a neutral mathematical choice. It encodes a **zero-sum
worldview**: every position competes for a fixed budget of weight that must sum
to exactly 1. If one token pulls harder, the others must pull less.

What does this mean in practice?

- The model is not asking *"which relationships matter?"*
- It is asking *"which single distribution of relationships is most statistically
  likely given my training corpus?"*

That is **interpolation**, not reasoning. The mechanism is optimized to
reproduce the most probable continuation of text it has already seen. It can
mimic extrapolation. It cannot **guarantee** constraint satisfaction across
novel combinations.

Statistical fluency is not logical grounding. A model can produce a sentence
that sounds like a proof while violating a constraint introduced three paragraphs
earlier — because nothing in the softmax path **requires** global consistency.
Consistency is hoped for. Not enforced.

---

## II. The "Next Token" Fallacy

Left-to-right token generation is not a minor implementation detail. It is a
**structural commitment** to a particular theory of cognition:

> Thought unfolds forward, one symbol at a time, with no obligation to revisit
> earlier commitments when later evidence arrives.

Consider a multi-step logical chain:

```
A supports B.  B entails C.  C contradicts D.  D was assumed at step 1.
```

A autoregressive model generates tokens left-to-right. By the time it reaches
the contradiction, the tokens committing to D are already emitted. The model
cannot **look backward** and propagate the state change. It can only:

- Hope the training distribution encoded enough implicit repair behavior, or
- Produce fluent text that papers over the inconsistency, or
- Hallucinate a resolution that was never computed

None of these are reasoning. They are **post-hoc narrative smoothing**.

Complex constraint resolution requires **bidirectional propagation** — energy
must flow through a structure until tensions resolve. That is not what next-token
prediction does. That is what a **graph under wave dynamics** does.

---

## III. What Statistical Models Actually Optimize

Be precise about what perplexity measures.

| Metric | What it actually captures |
|--------|---------------------------|
| Perplexity | How well the model predicts the next token in a corpus |
| BLEU / ROUGE | Surface overlap with reference text |
| "Helpfulness" ratings | Human preference for fluent responses |

None of these measure:

- Whether a contradiction was detected
- Whether a claim has typed verifier support
- Whether the resolution path is reproducible
- Whether the final state is the **lowest-energy stable configuration**

A model can ace perplexity and still be epistemologically bankrupt. TS-OS does
not reject language models. It rejects the claim that **perplexity is a proxy
for reasoning**.

---

## IV. The Solution — Tension Fields

TensionLM (`inference/tension_lm/`) replaces softmax competition with
**independent sigmoid tension** per token pair:

```
tau[t, w] = sigmoid( dot(q_t, k_w) / √d )
output[t] = Σ_w tau[t, w] · v_w
```

The difference is not cosmetic. It is architectural:

| Softmax attention | Sigmoid tension |
|-------------------|-----------------|
| Zero-sum weight budget | Independent per-pair scores |
| Competition between neighbors | Compositional pull |
| "Who wins?" | "Who matters, and how much?" |
| Statistical interpolation | Causal tension field |

A token can be pulled hard by **all** its neighbors simultaneously, or barely
pulled by any. There is no forced tradeoff. The model learns which relationships
carry tension without pretending only one relationship can dominate.

This is not attention with a different activation function. It is a **causal
tension graph** operating inside a recurrent semantic workspace — each position
exerts learned pull on its neighborhood, and the aggregate state evolves under
those pulls rather than under a probability race.

TensionForge (`inference/tension_forge/`) executes these fields on OpenCL when
available, exporting results as `.bogpk` artifacts for parity verification
against the CPU path. The math must match. The receipt must prove it.

---

## V. The Solution — Deterministic Constraint Resolution

Neural tension fields propose structure. They do not **decide** truth.

That is the job of the reasoner layer (`reasoner/`) and the bedrock VM
(`core-vm/`):

**BOGVM-0** is a 16-opcode deterministic wave-state virtual machine. Same
program, same input, same state — every time. No sampling in the proof path.
State transitions log to `.bogpk`. Reconstruction is SHA-256 verified.

**GOAT-TS** and the Verse Engine enforce:

```
Confidence is not proof. Typed verifier support is the proof boundary.
```

Models propose. Verifiers decide. Receipts record the decision trail.

The wave bridge (`reasoner/wave_bridge.py`) connects low-level VM states to
spectral metacompute (`reasoner/ts_metacompute/spectral/laplacian.py`) and
cognitive physics substrates. Constraint matrices flow down. Stable-state
receipts flow back up. Nothing is trusted without a hash.

---

## VI. Side-by-Side: Two Theories of Cognition

| Dimension | Token Prediction | TS-OS Cognitive Physics |
|-----------|------------------|-------------------------|
| Unit of thought | Next token | Stable constraint configuration |
| Mechanism | Softmax competition | Sigmoid tension + wave propagation |
| Direction | Left-to-right only | Bidirectional graph dynamics |
| Consistency | Hoped for | Enforced by constraint resolution |
| Confidence | Probability mass | ≠ proof; verifier receipts decide |
| State | Stateless window | Persistent living graph |
| Reproducibility | Stochastic sampling | Deterministic `.bogpk` artifact trail |
| Failure mode | Fluent hallucination | Quarantined claim + receipt |
| Success metric | Perplexity | Verifier acceptance + energy minimization |

---

## VII. What You Must Not Do

If you are evaluating or extending this system:

1. **Do not benchmark on perplexity alone.** Measure verifier acceptance rates,
   tension resolution, and receipt completeness.
2. **Do not treat LLM output as ground truth.** It is a proposal. Always.
3. **Do not skip `.bogpk` artifact trails.** They are the reproducibility contract.
4. **Do not conflate activation with proof.** High activation means hot, not true.
5. **Do not import softmax assumptions into tension fields.** The math is different.
   The epistemology is different. Do not pretend otherwise.

---

## VIII. Where This Leads

If token prediction is the ceiling, there is nothing left to invent — only scale
to chase. If cognitive physics is real, the path forward is:

1. **Tension fields** instead of softmax competition
2. **Living graphs** instead of stateless windows
3. **Verifier gates** instead of confidence scores
4. **Frozen receipts** instead of unrepeatable outputs

The mechanics are in [truth-graph.md](truth-graph.md). The infrastructure is
in [bogpk-pipeline.md](bogpk-pipeline.md). The code enforces all of it.

You cannot use this stack without choosing a side.

---

## References (Code, Not Faith)

| Claim | Implementation |
|-------|----------------|
| Sigmoid tension | `inference/tension_lm/model.py` |
| OpenCL parity | `inference/tension_forge/ops/fused_tension.py` |
| Living graph wave cycle | `core/wave.py`, `core/graph/wave_runner.py` |
| Verifier-gated reasoning | `reasoner/ts_reasoner/cognitive_physics_engine.py` |
| VM determinism | `core-vm/bogvm/vm.py`, `core-vm/bogvm/opcodes.py` |
| Artifact serialization | `shared/artifacts/bogpk.py` |
| VM → spectral bridge | `reasoner/wave_bridge.py` |

---

*The statistical paradigm is not wrong about language. It is wrong about cognition.
TS-OS is the alternative.*