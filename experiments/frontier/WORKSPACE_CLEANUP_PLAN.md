# Phase 0 Workspace Cleanup (P0.2)

## Goal
Rationalize the many historical copies in /home/boggersthefish/workspace/ so the active unified code (BoggersTheAI/) is obvious, while preserving lineage for reference.

## Recommended Moves (safe, non-destructive)
- mkdir -p workspace/history/
- Move (or git mv if tracked):
  - BAGI/ → history/BAGI/
  - GOAT-TS* (GOAT-TS/, GOAT-TS-DEVELOPMENT/, GOAT-TS-LITE/, GOAT-TS-SUPERLITE/, GOAT-OS/, GOAT-PUBLIC_TEST/, GOAT-SIMPLE/) → history/
  - TS-Reasoner-v0/ (the workspace/ copy) → history/
  - BoggersTheCIG/, BoggersTheCIG_v2/ → history/
  - TS-Core/, ts-llm/, TensionLM/ (if duplicate of bozo + inference) → history/
  - Other obvious old: cig-ts-engine/, TS-Codex-OS/, etc.

- In each moved dir, leave or add a README: "Historical. See workspace/BoggersTheAI/ for current unified TS-OS."

- In workspace/BoggersTheAI/README or docs: link to history/.

- Do not delete; just organize.

Run this when ready:
```bash
mkdir -p workspace/history
# then mv commands...
```

Current state (as of Phase 0): many staging copies from before the monorepo unification. The FRONTIER_PLAN treats BoggersTheAI/ as canonical.
