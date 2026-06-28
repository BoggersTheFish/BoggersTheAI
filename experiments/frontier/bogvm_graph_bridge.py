"""
BOGVM + Graph Bridge (start of Wave 0 subtask 1)

This provides a thin, import-safe bridge to make BOGVM programs first-class
citizens that can be attached to graph nodes and executed with receipts
fed back into the TS graph.

Usage in demos or future unification:
- attach_bogvm_program(graph, node_id, bogbin_path)
- run_attached_bogvm(graph, node_id) -> receipt

This will be merged into the main graph when import issues are resolved.
"""

import subprocess
import json
import tempfile
from pathlib import Path

def attach_bogvm_program(graph, node_id: str, bogbin_path: str):
    """Attach a BOGBIN program to a graph node as payload."""
    if node_id not in graph.nodes:
        raise ValueError(f"Node {node_id} not in graph")
    if not hasattr(graph, 'bogvm_programs'):
        graph.bogvm_programs = {}
    graph.bogvm_programs[node_id] = str(bogbin_path)
    # Also store in node payload if possible
    if hasattr(graph.nodes[node_id], 'payload'):
        graph.nodes[node_id].payload['bogvm_program'] = str(bogbin_path)
    elif isinstance(graph.nodes[node_id], dict):
        graph.nodes[node_id]['bogvm_program'] = str(bogbin_path)

def run_attached_bogvm(graph, node_id: str, receipt_dir: str = "/tmp"):
    """Run the attached BOGBIN for the node and return the receipt dict."""
    if not hasattr(graph, 'bogvm_programs') or node_id not in graph.bogvm_programs:
        raise ValueError(f"No BOGVM program attached to {node_id}")
    bogbin = graph.bogvm_programs[node_id]
    receipt_path = Path(receipt_dir) / f"bogvm_{node_id}_{int(__import__('time').time())}.json"
    cmd = ["python3", "-m", "core-vm.bogvm", "run", bogbin, "--receipt", str(receipt_path)]
    subprocess.check_call(cmd)
    with open(receipt_path) as f:
        receipt = json.load(f)
    # Feed back into graph as receipt or tension update
    if hasattr(graph, 'add_receipt'):
        graph.add_receipt(node_id, receipt)
    return receipt

# Example for future:
# g = ...
# attach_bogvm_program(g, some_node, "/path/to/program.bogbin")
# r = run_attached_bogvm(g, some_node)
# print(r["execution_status"])