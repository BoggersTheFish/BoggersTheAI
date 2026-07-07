# CLI

Entry point:

```bash
boggers
```

This resolves to `BoggersTheAI.interface.chat:run_chat`.

## Common Commands

| Command | Action |
|---------|--------|
| `help` or `/help` | List available commands. |
| `status` or `/status` | Show wave engine status, graph size, and current tension. |
| `graph` or `graph stats` | Show graph metrics and topic distribution. |
| `trace` or `trace show` | Print the beginning of the latest local trace file. |
| `wave pause` | Stop the background wave thread. |
| `wave resume` | Restart the background wave thread. |
| `improve` | Run the configured self-improvement trigger. Training remains gated by receipt eligibility. |
| `health` | Run registered health checks. |
| `history` | Show recent conversation turn nodes for the current session. |
| `exit` or `quit` | Save graph state, stop threads, and exit. |

Any other input is sent to `rt.ask(query)` as a natural-language query. The
verifier-gated formal path is still `TSKernel.transact()` under the hood for
supported formal grammar; confidence-only output is not accepted truth.

## Kernel Commands

Useful kernel demo commands:

```bash
boggers kernel demo
boggers kernel run-seeds
boggers kernel replay artifacts/seed_receipts/seed_001_chained_syllogism.receipt.json
boggers kernel audit artifacts/seed_receipts/seed_001_chained_syllogism.receipt.json
```

The seed runner can also be invoked directly:

```bash
python -m experiments.frontier.run_seed_tasks
```
