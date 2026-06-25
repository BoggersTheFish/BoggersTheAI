# BOGPK Pipeline — Unified Artifact Serialization

Every TS-OS layer serializes state through the `.bogpk` binary container format.
This enforces a perfect, reproducible artifact trail across all modules.

## Format

BOGPK-0.1 is the compact reconstruction blueprint (see `core-vm/BOGPK_SPEC.md`):

```
BOGPKHeader → TransformBasisStream → ChunkResidualIndexStream → ResidualPatchStream → OptionalHashStream
```

- Magic: `BOGPK1`
- Chunk sizes: 16, 32, 64, 128 bytes
- Proof authority: BOGVM-0 deterministic reconstruction + SHA-256 verification
- `.bogpk` is **not** proof authority — it is compressed storage

## Layer Mapping

| Layer | Artifact Kind | Module |
|-------|--------------|--------|
| `core-vm/` | `vm_state` | `core-vm/artifact_log.py` |
| `inference/` | `tension_field` | `inference/artifact_export.py` |
| `reasoner/` | `reasoner_receipt` | `reasoner/artifact_receipts.py` |
| Any | `wave_snapshot` | `shared/artifacts/bogpk.py` |

## Usage

```python
from shared.artifacts import (
    ArtifactKind,
    serialize_artifact,
    deserialize_artifact,
    artifact_trail_dir,
)

# Serialize JSON receipt
serialize_artifact(
    {"opcode": "WAVE", "tension": 0.42},
    "artifacts/core-vm/state_001.bogpk",
    kind=ArtifactKind.VM_STATE,
)

# Serialize raw bytes (tension field matrix)
import numpy as np
from inference.artifact_export import export_tension_field
export_tension_field(np.zeros((8, 8)), layer=2, prompt="the cat sat")

# Deserialize
raw_bytes, metadata = deserialize_artifact("artifacts/core-vm/state_001.bogpk")
```

## CLI (BOGVM-0)

```bash
python -m bogvm pack input.txt output.bogpk --chunk-size 64
python -m bogvm unpack output.bogpk restored.txt
```

Run from `core-vm/` directory or with `PYTHONPATH=core-vm`.

## Compression Threshold

Aggregate `.bogpk` container-to-input ratio: **0.960** (below 1.0 = smaller than input).
Individual fixtures may vary. JSON `.bog` remains the audit/debug format.