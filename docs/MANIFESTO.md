# MANIFESTO — The Axioms of Cognitive Physics

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   If you came here for a wrapper API around a statistical language model,      ║
║   turn back now.                                                             ║
║                                                                              ║
║   If you came here because standard architectures have hit a logical wall,   ║
║   read on. The mechanics of reasoning belong in the public domain.            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

This document is the front door to BoggersTheAI — the unified TS-OS monorepo.
You cannot use this system without engaging with what it claims about cognition.
That is not a bug. It is the design.

---

## I. The Core Axiom

**Thought is not a statistical accident.**

A fluent sentence is not a thought. A high-probability token is not a conclusion.
A confident model is not a reasoner.

**Cognitive physics** is the claim that thought is the **stable configuration of
constraints under wave propagation**. Meaning is not predicted forward one token
at a time. It **settles** — the way a physical field finds equilibrium when
competing forces are applied and released.

In TS-OS terms:

> Everything that exists is a stable cluster of constraints.

A concept is a node under tension. A relation is not a label — it is a
restriction on what configurations are allowed. Reasoning is not generation;
it is **propagation until the graph stops fighting itself**.

The operational loop shared across every layer of this monorepo:

```
Propagate → Relax → Break → Evolve
```

This runs in the living graph (`core/`), in TensionLM's sigmoid tension fields
(`inference/tension_lm/`), and in BOGVM-0's 16-opcode deterministic wave-state
machine (`core-vm/`). Same physics. Different substrates.

---

## II. The Rejection of the Black Box

Standard models offer **statistical fluency without logical grounding**.

They can sound correct while being wrong. They can be wrong while sounding
confident. They can interpolate training distributions elegantly and still fail
to extrapolate a single novel constraint chain. That is not a training problem
alone. It is an **epistemological architecture problem**.

TS-OS demands something different: **explicit, inspectable receipts**.

```
Substrates expose tension → Models propose → TS verifies → Receipts decide
```

| What the industry calls… | What TS-OS requires |
|--------------------------|---------------------|
| Confidence | Typed verifier support |
| Output | Proposal |
| Proof | Receipt with hash chain |
| State | Frozen artifact trail |

**If a system cannot mathematically show how it arrived at a state, it is not
reasoning. It is hallucinating elegantly.**

Language models in this stack are **proposers**, not oracles. They may suggest
candidates. They may synthesize when the graph is thin. They do not decide.
The proof boundary is external, typed, and logged.

Confidence is not proof. The softmax output is not the verdict. The receipt is.

---

## III. The Open-Source Mandate

This work is open source not as a distribution strategy, but as a **scientific
necessity**.

You cannot rewrite the rules of cognition behind a proprietary API. You cannot
ask the research community to trust a black box while claiming to have
superseded the black box. If cognitive physics is real, its mechanics must be
**inspectable, reproducible, and forkable**.

That means:

- **Deterministic bedrock** — BOGVM-0 executes the same program to the same
  state, every time, on every machine.
- **Compressed artifact trails** — every layer serializes through `.bogpk`, a
  highly packed binary container governed by `core-vm/BOGPK_SPEC.md`.
- **Verifier-gated acceptance** — nothing enters the Truth Graph without typed
  support, regardless of how persuasive the proposal sounds.

Closed-source "reasoning" is indistinguishable from marketing. Open-source
reasoning with receipts is falsifiable science.

---

## IV. What This Repository Is

BoggersTheAI is not a chatbot. It is a **Thinking System Operating System**
(TS-OS) — a strict hierarchical stack that mirrors how the system actually
computes:

| Layer | Path | Role |
|-------|------|------|
| **Bedrock** | `core-vm/` | BOGVM-0 — 16-opcode deterministic wave-state VM |
| **Inference** | `inference/` | TensionLM + TensionForge — neural execution without softmax competition |
| **Reasoner** | `reasoner/` | GOAT-TS, Verse Engine, spectral metacompute — constraint resolution |
| **Runtime** | `core/`, `interface/` | Living graph, wave cycle, autonomous loop |
| **Artifacts** | `shared/artifacts/` | Unified `.bogpk` serialization across all layers |

Data crosses layer boundaries **only** through `.bogpk`. Whether BOGVM-0 logs a
state transition or TensionLM exports a tension field, the trail is compressed,
hashed, and reproducible.

---

## V. Epistemological Rules (Non-Negotiable)

1. **No substrate accepts its own output.** Proposals are never self-verifying.
2. **Receipts are proof authority.** `.bogpk` containers are reconstruction
   blueprints — not proof. The VM and verifier decide.
3. **Artifact trails are mandatory.** A state change without a receipt is untrusted.
4. **Simulators are bounded.** Cognitive physics substrates in `reasoner/` are
   deterministic contracts — not claims of literal photonic hardware or retrocausality.
5. **Archive satellites stay frozen.** Fifty-two historic repositories merged into
   this claim boundary. Development happens here only.

---

## VI. How to Read This Stack (The Trap You Walked Into)

You came for code. To use it correctly, you must read the rulebook.

**In this order:**

1. **[anti-token-prediction.md](anti-token-prediction.md)** — Why the statistical
   paradigm fails. The deconstruction.
2. **[truth-graph.md](truth-graph.md)** — The exact mechanics of the alternative.
   The payload.
3. **[bogpk-pipeline.md](bogpk-pipeline.md)** — How resolution paths are frozen,
   hashed, and exported.
4. **[directory-structure.md](directory-structure.md)** — Where each substrate
   lives in the monorepo.

You cannot plug in an API and pretend none of this exists. The documentation
is the interface to the epistemology. The code enforces it.

---

## VII. The Claim Boundary

Fifty-two historic repositories were merged into this monorepo. Four active
satellites are archived with redirect notices:

| Former satellite | Monorepo home |
|------------------|---------------|
| BoggersTheMind | `core/`, `interface/`, `entities/`, `mind/` |
| BoggersTheLLM | `inference/` (language substrate) |
| bozo (TensionLM) | `inference/tension_lm/` |
| TS-Reasoner-v0 | `reasoner/ts_reasoner/` |
| bogbin (BOGVM-0) | `core-vm/bogvm/` |

The boundary is closed. The physics is unified. The receipts are public.

---

*TS-OS Manifesto — BoggersTheAI monorepo. Cognitive physics belongs to everyone.*