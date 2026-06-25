# Metrics and Evaluation TODO

The codebase exposes runtime graph and system metrics through `core/metrics.py`, the CLI, tests, and the dashboard `/metrics` endpoint. It does not currently include a top-level evaluation report, benchmark output, or reproducible results artifact.

Before publishing performance or quality claims, add a small `docs/` or `results/` artifact that records:

- dataset or workload used for evaluation;
- configuration, model names, and optional dependency versions;
- graph size, wave-cycle settings, and persistence backend;
- measured latency, confidence, tension, and stability metrics;
- known failure cases and reproduction commands.
