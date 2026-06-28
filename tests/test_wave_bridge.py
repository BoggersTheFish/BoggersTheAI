"""Wave virtualization bridge: VM state → spectral → cognitive physics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REASONER = ROOT / "reasoner"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REASONER))


def test_vm_state_to_signed_graph():
    from wave_bridge import run_spectral_metacompute, vm_state_to_signed_graph

    vm_state = {
        "nodes": {
            "0": {"name": "A"},
            "1": {"name": "B"},
            "2": {"name": "C"},
        },
        "edges": {
            "0": {"src": "0", "dst": "1", "type": "support", "weight": 1.0},
            "1": {"src": "1", "dst": "2", "type": "support", "weight": 1.0},
        },
        "activation_current": {"0": 500, "1": 300, "2": 100},
        "tension_current": {"0": 0, "1": 0, "2": 0},
    }
    graph = vm_state_to_signed_graph(vm_state)
    spectral = run_spectral_metacompute(graph)
    assert spectral["laplacian_dimension"] == 3
    assert spectral["edge_count"] == 2
    assert "matrix_hash" in spectral


def test_wave_virtualization_writes_bogpk(tmp_path):
    from wave_bridge import run_wave_virtualization

    vm_state = {
        "nodes": {"0": {"name": "A"}, "1": {"name": "B"}},
        "edges": {"0": {"src": "0", "dst": "1", "type": "support", "weight": 1.0}},
        "activation_current": {},
        "tension_current": {},
    }
    result = run_wave_virtualization(
        vm_state,
        question="Does A support B?",
        artifacts_root=tmp_path,
    )
    assert result["all_gates_passed"] is True
    assert Path(result["bogpk_path"]).exists()
    assert Path(result["bogpk_path"]).suffix == ".bogpk"
