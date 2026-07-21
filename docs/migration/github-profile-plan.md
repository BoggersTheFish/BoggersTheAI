# GitHub Profile Optimization & Pinning Plan (aspirational)

Planning document for `@BoggersTheFish` presentation. **This is not a completion certificate.**

**Current flagship remote:** `BoggersTheFish/BoggersTheAI`
**Planned rename:** `BoggersTheFish/thinking-system` (not done)

---

## 1. Recommended pinned repositories (when ready)

1. **`BoggersTheAI`** (until rename) / **`thinking-system`** (after rename) — flagship monorepo
2. **`bogbin`** — independent verified storage substrate
3. **`ts-spear`** — independent applied project
4. Other pins as the maintainer chooses

Do **not** pin a non-existent `thinking-system` remote before rename.

---

## 2. Satellite archive policy (current)

| Repository | Action now | Reason |
| :--- | :--- | :--- |
| `BoggersTheAI` | Keep active | Canonical migration in progress |
| `TS-Core`, `cig-ts-engine`, `TS-LAB`, `TS-OS`, `ts-chat-language`, `TensionForge`, `Ten-SON-LM`, `tsq`, `ts-exodus`, `ts-lm-genesis`, `TS-Benchmarks` | **Do not archive** | Destinations empty or partial; not CONSOLIDATED in import-ledger |
| `TensionLM`, `TS-Reasoner-v0` | Historical reference OK if already archived | Not proof of monorepo port |
| `bogbin`, `ts-spear` | Keep active | Independent products |

Archive only after:

1. Import-ledger row is **CONSOLIDATED** with verified source SHA
2. Destination paths contain tracked code + tests
3. Explicit maintainer decision

---

## 3. After monorepo is genuinely complete

Then (and only then): rename remote, update badges/URLs, and reconsider satellite archival.
