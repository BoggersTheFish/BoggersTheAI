# PRIME M26 — Comparative Cognition Arena v0.1

Status:

    DEVELOPMENT PROTOCOL

Purpose:

    Compare verifier-governed adaptive explicit representation learning
    against learned recurrent state.

This is diagnostic capability cartography.

It is not designed to declare one architecture universally superior.

---

# Conditions

REACTIVE

    Current observation only.

H8

    Raw trailing 8-observation history.

H16

    Raw trailing 16-observation history.

GRU32

    Learned recurrent neural state.

    Architecture:

        GRUCell
        input dimension 1
        hidden dimension 32
        linear binary output

    Online optimization:

        Adam
        learning rate 0.01
        deterministic CPU execution
        truncated replay length 32
        gradient clipping 1.0

PRIME

    CompositionalAdaptiveConstructionEngine

    maximum lag:
        16

    maximum candidate field:
        512

    higher-order scaffolds:
        enabled

    verifier authority:
        unchanged

    learned neural machinery:
        none

---

# Development

Development seeds:

    26000..26005

Six stream seeds.

No held-out evaluation is authorized by this protocol.

Future evaluation seeds are reserved but blocked:

    36000..36031

---

# Episode

Scored events per world:

    1536

Final window:

    256

All conditions for one task/seed receive exactly the same observation stream.

---

# Task family A — Explicit relational structure

CURRENT

LAG-1

LAG-4

XOR-1-4

EQ-1-4

AND-1-4

OR-2-7

XOR-1-2-3

These largely match PRIME's explicit construction language.

---

# Task family B — Representational scaling

LAG-8

LAG-16

XOR-1-8

XOR-1-16

MAJORITY-16

These test longer temporal dependencies and scaling cost.

MAJORITY-16 is not directly represented by the current PRIME
construction grammar.

---

# Task family C — Recurrent latent state

RUNNING-PARITY

MOD3-ONES

TOGGLE-ON-11

RUN-LENGTH-PARITY

These require persistent state summaries not naturally expressible as fixed
bounded lag expressions.

They deliberately provide learned recurrence with genuine home-field tasks.

---

# Task family D — Nonstationarity

XOR-TO-AND

First half:

    XOR(LAG1, LAG4)

Second half:

    AND(LAG1, LAG4)

No explicit regime-change signal is supplied.

---

# Measurements

For every condition/world:

    online AULC;
    total accuracy;
    final-window accuracy;
    cumulative mistakes.

For PRIME:

    first authorization event;
    active construction count;
    predictive-partition recovery where an explicit target exists;
    receipt-chain integrity.

For GRU:

    final training loss;
    trainable parameter count.

---

# Interpretation

The benchmark distinguishes:

    symbolic / relational construction strength;

    raw-memory scaling;

    recurrent-state strength;

    nonstationary adaptation.

A mixed result is desirable.

If one architecture wins every family, benchmark bias must be considered.

---

# Claim boundary

Development results are descriptive.

No held-out scientific claim may be made from this protocol.

No AGI, general intelligence or universal superiority claim is permitted.
