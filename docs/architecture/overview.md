# Thinking System Architecture Overview

Thinking System is structured into strict, decoupled layers where foundational authority flows unidirectionally from core verification up to application interfaces.

```text
ts-core
  ↓
ts-ir + ts-artifacts
  ↓
ts-verifiers
  ↓
ts-kernel
  ↓
ts-graph + ts-reasoner
  ↓
ts-language + ts-runtime
  ↓
CLI / Lab / Dashboard / Chat
```

---

## Layer Definitions

1. **Foundational Layer (`ts-core`, `ts-ir`, `ts-artifacts`):**
   Defines foundational data structures, intermediate representation (TSIR), schemas, and content-addressable receipt hashing.

2. **Verifier Authority Layer (`ts-verifiers`):**
   Contains deterministic proof checkers (arithmetic verifiers, observation predicate verifiers, structural verifiers).

3. **Transaction Kernel (`ts-kernel`):**
   Manages atomic state transactions, obligation enforcement, tension accounting, commit/quarantine/branch decisions, and replay verification.

4. **Graph & Reasoning Layer (`ts-graph`, `ts-reasoner`):**
   Implements universal living graph dynamics, wave runner cycles, and constraint resolution over state nodes.

5. **Language & Runtime Layer (`ts-language`, `ts-runtime`):**
   TSLC language compiler, deterministic dialogue substrate (DDS), TSQ quantization, and runtime composition.

6. **Applications & Interfaces (`apps/`):**
   CLI (`ts`), TS-LAB workbench (`apps/lab`), FastAPI Dashboard (`apps/dashboard`), and Chat interface (`apps/chat`).
