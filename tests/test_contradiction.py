from __future__ import annotations

from BoggersTheAI.core.contradiction import (
    Contradiction,
    detect_contradictions,
    resolve_contradiction,
)
from BoggersTheAI.core.types import Node


def _make_node(nid, content, topics, activation=0.8, stability=0.7):
    return Node(
        id=nid,
        content=content,
        topics=topics,
        activation=activation,
        stability=stability,
    )


def test_no_contradictions_when_no_overlap():
    nodes = {
        "a": _make_node("a", "cats are good", ["animals"]),
        "b": _make_node("b", "python is great", ["programming"]),
    }
    result = detect_contradictions(nodes)
    assert len(result) == 0


def test_contradiction_detected_on_antonyms():
    nodes = {
        "a": _make_node("a", "the result is true", ["logic"]),
        "b": _make_node("b", "the result is false", ["logic"]),
    }
    result = detect_contradictions(nodes)
    assert len(result) >= 1
    assert result[0].node_a == "a"
    assert result[0].node_b == "b"


def test_no_contradiction_below_activation_threshold():
    nodes = {
        "a": _make_node("a", "the result is true", ["logic"], activation=0.1),
        "b": _make_node("b", "the result is false", ["logic"], activation=0.1),
    }
    result = detect_contradictions(nodes, activation_threshold=0.5)
    assert len(result) == 0


def test_resolve_contradiction_weakens_lower():
    nodes = {
        "a": _make_node("a", "true claim", ["topic"], stability=0.3),
        "b": _make_node("b", "false claim", ["topic"], stability=0.8),
    }
    c = Contradiction(node_a="a", node_b="b", reason="test", severity=0.5)
    resolve_contradiction(nodes, c, strategy="weaken_lower")
    assert nodes["a"].activation < 0.8


def test_resolve_contradiction_collapse():
    nodes = {
        "a": _make_node("a", "true claim", ["topic"], stability=0.3),
        "b": _make_node("b", "false claim", ["topic"], stability=0.8),
    }
    c = Contradiction(node_a="a", node_b="b", reason="test", severity=0.5)
    resolve_contradiction(nodes, c, strategy="collapse_lower")
    assert nodes["a"].collapsed is True
