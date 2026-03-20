from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List
from xml.etree.ElementTree import Element, SubElement, tostring

from ..types import Edge, Node

logger = logging.getLogger("boggers.graph.export")


def export_graphml(
    nodes: Dict[str, Node],
    edges: List[Edge],
    path: str | Path,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    ns = "http://graphml.graphstruct.org/xmlns"
    root = Element("graphml", xmlns=ns)

    for attr_name, attr_type in [
        ("content", "string"),
        ("topics", "string"),
        ("activation", "double"),
        ("stability", "double"),
        ("base_strength", "double"),
        ("collapsed", "boolean"),
    ]:
        key_el = SubElement(root, "key")
        key_el.set("id", attr_name)
        key_el.set("for", "node")
        key_el.set("attr.name", attr_name)
        key_el.set("attr.type", attr_type)

    for attr_name, attr_type in [
        ("weight", "double"),
        ("relation", "string"),
    ]:
        key_el = SubElement(root, "key")
        key_el.set("id", attr_name)
        key_el.set("for", "edge")
        key_el.set("attr.name", attr_name)
        key_el.set("attr.type", attr_type)

    graph_el = SubElement(root, "graph", edgedefault="directed")

    for node in nodes.values():
        node_el = SubElement(graph_el, "node", id=node.id)
        _add_data(node_el, "content", node.content[:500])
        _add_data(node_el, "topics", ",".join(node.topics))
        _add_data(node_el, "activation", str(round(node.activation, 6)))
        _add_data(node_el, "stability", str(round(node.stability, 6)))
        _add_data(node_el, "base_strength", str(round(node.base_strength, 6)))
        _add_data(node_el, "collapsed", str(node.collapsed).lower())

    for i, edge in enumerate(edges):
        edge_el = SubElement(
            graph_el,
            "edge",
            id=f"e{i}",
            source=edge.src,
            target=edge.dst,
        )
        _add_data(edge_el, "weight", str(round(edge.weight, 6)))
        _add_data(edge_el, "relation", edge.relation)

    xml_bytes = tostring(root, encoding="unicode", xml_declaration=True)
    target.write_text(xml_bytes, encoding="utf-8")
    logger.info(
        "Exported GraphML: %s (%d nodes, %d edges)", target, len(nodes), len(edges)
    )
    return target


def _add_data(parent: Element, key: str, value: str) -> None:
    d = SubElement(parent, "data", key=key)
    d.text = value


def export_json_ld(
    nodes: Dict[str, Node],
    edges: List[Edge],
    path: str | Path,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    graph_nodes = []
    for node in nodes.values():
        graph_nodes.append(
            {
                "@id": node.id,
                "@type": "Concept",
                "content": node.content,
                "topics": node.topics,
                "activation": round(node.activation, 6),
                "stability": round(node.stability, 6),
                "baseStrength": round(node.base_strength, 6),
                "collapsed": node.collapsed,
            }
        )

    graph_edges = []
    for edge in edges:
        graph_edges.append(
            {
                "@type": "Relation",
                "source": edge.src,
                "target": edge.dst,
                "weight": round(edge.weight, 6),
                "relation": edge.relation,
            }
        )

    payload = {
        "@context": {
            "Concept": "https://boggersthefish.com/schema/Concept",
            "Relation": "https://boggersthefish.com/schema/Relation",
            "content": "https://boggersthefish.com/schema/content",
            "activation": "https://boggersthefish.com/schema/activation",
            "stability": "https://boggersthefish.com/schema/stability",
        },
        "@graph": graph_nodes + graph_edges,
    }

    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info(
        "Exported JSON-LD: %s (%d nodes, %d edges)", target, len(nodes), len(edges)
    )
    return target
