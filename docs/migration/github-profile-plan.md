# GitHub Profile Optimization & Pinning Plan (aspirational)

Planning document for `@BoggersTheFish` presentation. **This is not a completion certificate.**

**Canonical flagship remote:** `BoggersTheFish/thinking-system`
**Former remote:** `BoggersTheFish/BoggersTheAI` (renamed after merge `9786e098…`)

---

## 1. Recommended pinned repositories (when ready)

1. **`thinking-system`** — flagship monorepo (formerly `BoggersTheAI`)
2. **`bogbin`** — independent verified storage substrate
3. **`ts-spear`** — independent applied project
4. Other pins as the maintainer chooses

---

## 2. Satellite archive policy (current)

| Repository | Action now | Reason |
| :--- | :--- | :--- |
| `thinking-system` (formerly `BoggersTheAI`) | Keep active | Canonical monorepo (alpha) |
| `TS-Core`, `cig-ts-engine`, `TS-LAB`, `TS-OS`, `ts-chat-language`, `TensionForge`, `Ten-SON-LM`, `tsq`, `ts-exodus`, `ts-lm-genesis`, `TS-Benchmarks` | **Do not archive** | Destinations empty or partial; not CONSOLIDATED in import-ledger |
| `TensionLM`, `TS-Reasoner-v0` | Historical reference OK if already archived | Not proof of monorepo port |
| `bogbin`, `ts-spear` | Keep active | Independent products |

Archive only after:

1. Import-ledger row is **CONSOLIDATED** with verified source SHA
2. Destination paths contain tracked code + tests
3. Explicit maintainer decision

---

## 3. After monorepo package migration is genuinely complete

Repository rename is **done**. Remaining work: physical package moves, satellite imports with verified SHAs, and only then reconsider satellite archival.
