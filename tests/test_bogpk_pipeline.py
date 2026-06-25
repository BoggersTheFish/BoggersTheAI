"""Verify unified .bogpk artifact pipeline across TS-OS layers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core-vm"))


def test_serialize_and_deserialize_json_artifact(tmp_path):
    from shared.artifacts import ArtifactKind, deserialize_artifact, serialize_json_payload

    payload = {"layer": "test", "tension": 0.42, "opcode": "WAVE"}
    path = serialize_json_payload(payload, tmp_path / "test_receipt", kind=ArtifactKind.VM_STATE)
    assert path.suffix == ".bogpk"
    assert path.exists()

    raw, container = deserialize_artifact(path)
    import json

    restored = json.loads(raw.decode("utf-8"))
    assert restored["tension"] == 0.42
    assert container["artifact_kind"] == "vm_state"


def test_artifact_trail_dirs(tmp_path):
    from shared.artifacts.bogpk import artifact_trail_dir

    vm_trail = artifact_trail_dir("core-vm", tmp_path)
    inf_trail = artifact_trail_dir("inference", tmp_path)
    rea_trail = artifact_trail_dir("reasoner", tmp_path)
    assert vm_trail.exists()
    assert inf_trail.exists()
    assert rea_trail.exists()


def test_tension_forge_cpu_fallback(tmp_path):
    import numpy as np

    from inference.tension_forge.runtime import TensionForgeRuntime

    runtime = TensionForgeRuntime(prefer_gpu=False)
    q = np.random.randn(4, 8).astype(np.float32)
    k = np.random.randn(4, 8).astype(np.float32)
    field = runtime.compute_tension_field(q, k)
    assert field.shape == (4,)
    assert (field >= 0).all() and (field <= 1).all()

    out = runtime.execute_and_serialize(q, k, tmp_path / "tension_test")
    assert out.suffix == ".bogpk"