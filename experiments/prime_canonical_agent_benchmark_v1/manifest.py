"""Frozen implementation constants for PRIME Canonical Agent Benchmark v1."""

BENCHMARK_VERSION = "prime-canonical-agent-benchmark-v1"

# Frozen before any evaluation-seed result inspection.
DEVELOPMENT_SEEDS = tuple(range(0, 32))
EVALUATION_SEEDS = tuple(range(1000, 1128))

PERMITTED_DEPTHS = (0, 1, 2, 4)
CONDITIONS = (
    "REACTIVE",
    "FIXED-H1",
    "FIXED-H2",
    "FIXED-H4",
)

# The dependency-free apparatus is frozen at this horizon before adaptive
# PRIME is implemented.
EPISODES = 64
DECISION_STEPS_PER_EPISODE = 64
WARMUP_STEPS = 4
FINAL_WINDOW_EPISODES = 8

# Deterministic exploration: exactly 1 in every 10 decisions is exploratory.
EXPLORATION_PERIOD = 10

# Canonical integer scaling for learning-curve statistics.
PPM = 1_000_000
