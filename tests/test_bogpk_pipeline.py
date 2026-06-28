"""Verify unified .bogpk artifact pipeline across TS-OS layers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core-vm"))


def test_serialize_and_deserialize_json_artifact(tmp_path):
    from shared.artifacts import (
        ArtifactKind,
        deserialize_artifact,
        serialize_json_payload,
    )

    payload = {"layer": "test", "tension": 0.42, "opcode": "WAVE"}
    path = serialize_json_payload(
        payload, tmp_path / "test_receipt", kind=ArtifactKind.VM_STATE
    )
    assert path.suffix == ".bogpk"
    assert path.exists()

    raw, container = deserialize_artifact(path)
    restored = json.loads(raw.decode("utf-8"))
    assert restored["tension"] == 0.42
    assert container["artifact_kind"] == "vm_state"
    assert container["format"] == "BOG-2.0"
    assert container["vm_format"] == "BOGBIN-2.0"


def test_artifact_trail_dirs(tmp_path):
    from shared.artifacts.bogpk import artifact_trail_dir

    vm_trail = artifact_trail_dir("core-vm", tmp_path)
    inf_trail = artifact_trail_dir("inference", tmp_path)
    rea_trail = artifact_trail_dir("reasoner", tmp_path)
    assert vm_trail.exists()
    assert inf_trail.exists()
    assert rea_trail.exists()


def test_tension_forge_cpu_fallback(tmp_path):
    from inference.tension_forge.bogpk_runtime import TensionForgeRuntime

    runtime = TensionForgeRuntime(prefer_gpu=False)
    q = np.random.randn(4, 8).astype(np.float32)
    k = np.random.randn(4, 8).astype(np.float32)
    field = runtime.compute_tension_field(q, k)
    assert field.shape == (4,)
    assert (field >= 0).all() and (field <= 1).all()

    out = runtime.execute_and_serialize(q, k, tmp_path / "tension_test")
    assert out.suffix == ".bogpk"


def test_tension_field_export_schema_validation(tmp_path):
    from inference.artifact_export import export_tension_field, verify_exported_artifact

    matrix = np.random.randn(4, 8).astype(np.float32)
    path = export_tension_field(
        matrix, layer=2, prompt="the cat sat", artifacts_root=tmp_path
    )
    container = verify_exported_artifact(path, expected_shape=[4, 8])
    assert container["artifact_kind"] == "tension_field"
    meta = container["artifact_metadata"]
    assert meta["layer"] == 2
    assert meta["shape"] == [4, 8]


def test_tension_metadata_rejects_unknown_keys(tmp_path):
    from inference.artifact_export import _validate_tension_metadata
    from shared.artifacts import BogpkValidationError

    with pytest.raises(BogpkValidationError):
        _validate_tension_metadata({"layer": 1, "unknown_key": True})
