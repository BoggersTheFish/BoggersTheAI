#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.request
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Set, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT) if 'WORKSPACE_ROOT' in globals() else str(PROJECT_ROOT))

from BoggersTheAI.interface.runtime import RuntimeConfig, BoggersRuntime
from BoggersTheAI.core.graph.universal_living_graph import UniversalLivingGraph
from BoggersTheAI.core.embeddings import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("boggers.seed_graph")

WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"


def http_get_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BoggersTheAI-Seeder/1.0 (contact: boggersthefish@github)"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code == 429 and attempt < 3:
                wait_time = (attempt + 1) * 3.0
                logger.info("Rate limited (429). Retrying in %.1fs...", wait_time)
                time.sleep(wait_time)
                continue
            raise
        except Exception:
            raise


def fetch_entity(qid: str) -> dict | None:
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "languages": "en",
        "format": "json"
    }
    url = f"{WIKIDATA_API_URL}?{urllib.parse.urlencode(params)}"
    try:
        data = http_get_json(url)
        entities = data.get("entities", {})
        return entities.get(qid)
    except Exception as exc:
        logger.warning("Failed to fetch entity %s: %s", qid, exc)
        return None


def get_entity_claims(entity: dict) -> Dict[str, List[str]]:
    claims_dict = {}
    claims = entity.get("claims", {})
    # P279: subclass of, P31: instance of, P361: part of, P1269: facet of
    target_properties = ["P279", "P31", "P361", "P1269"]
    for prop in target_properties:
        prop_claims = claims.get(prop, [])
        qids = []
        for claim in prop_claims:
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})
            if isinstance(value, dict) and value.get("entity-type") == "item":
                qids.append(value.get("id"))
        if qids:
            claims_dict[prop] = qids
    return claims_dict


def crawl_wikidata(seed_qids: List[str], max_nodes: int) -> tuple[Dict[str, dict], List[tuple[str, str, str, float]]]:
    queue = list(seed_qids)
    visited = set()
    node_data: Dict[str, dict] = {}
    edges: List[tuple[str, str, str, float]] = [] # (src, dst, prop, weight)
    
    logger.info("Starting crawl with seed QIDs: %s, max_nodes: %d", seed_qids, max_nodes)
    
    while queue and len(node_data) < max_nodes:
        qid = queue.pop(0)
        if qid in visited:
            continue
        visited.add(qid)
        
        # Sleep 0.5s to prevent immediate rate limit
        time.sleep(0.5)
        entity = fetch_entity(qid)
        if not entity:
            continue
            
        labels = entity.get("labels", {})
        label = labels.get("en", {}).get("value", qid)
        
        descriptions = entity.get("descriptions", {})
        desc = descriptions.get("en", {}).get("value", "No description available")
        
        aliases_list = entity.get("aliases", {}).get("en", [])
        aliases = [a.get("value") for a in aliases_list if a.get("value")]
        
        node_data[qid] = {
            "id": qid,
            "label": label,
            "description": desc,
            "aliases": aliases
        }
        logger.info("Crawled node [%d/%d]: %s (%s)", len(node_data), max_nodes, label, qid)
        
        claims = get_entity_claims(entity)
        for prop, target_qids in claims.items():
            for target in target_qids:
                # Add to queue if not visited
                if target not in visited and target not in queue:
                    queue.append(target)
                
                # Weight by property type
                weight = 0.8 if prop in ["P279", "P31"] else 0.6
                edges.append((qid, target, prop, weight))
                
    return node_data, edges


def main():
    parser = argparse.ArgumentParser(description="Seed the TS Engine SQLite graph with Wikidata.")
    parser.add_argument("--seeds", type=str, default="Q11660,Q11023,Q21198", help="Comma-separated seed Wikidata QIDs (default: AI, computer science, etc.)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of nodes to seed")
    parser.add_argument("--db", type=str, default=None, help="Database path override")
    args = parser.parse_args()
    
    seed_list = [s.strip() for s in args.seeds.split(",") if s.strip()]
    nodes_raw, edges_raw = crawl_wikidata(seed_list, args.limit)
    
    logger.info("Seeding data into SQLite graph...")
    cfg = RuntimeConfig()
    if args.db:
        cfg.sqlite_path = args.db
        
    runtime = BoggersRuntime(config=cfg)
    graph = runtime.graph
    
    # 1. Populate node embeddings
    embedder = getattr(graph, "_embedder", None)
    logger.info("Generating embeddings for crawled entities...")
    
    nodes_created = 0
    for qid, nd in nodes_raw.items():
        content = f"{nd['label']}: {nd['description']}"
        topics = [nd['label'].lower()] + [a.lower() for a in nd['aliases']]
        
        emb = []
        if embedder is not None:
            try:
                emb = embedder.embed(content)
            except Exception as exc:
                logger.warning("Failed to generate embedding for %s: %s", qid, exc)
                
        node = graph.add_node(
            node_id=qid,
            content=content,
            topics=topics,
            activation=0.5,
            stability=0.8,
            base_strength=0.7
        )
        if emb:
            node.embedding = emb
        nodes_created += 1
        
    logger.info("Created %d nodes in SQLite graph.", nodes_created)
    
    # 2. Populate edges
    edges_created = 0
    for src, dst, prop, weight in edges_raw:
        if src in nodes_raw and dst in nodes_raw:
            graph.add_edge(src, dst, weight=weight)
            edges_created += 1
            
    # 3. Add semantic similarity edges if embeddings exist
    semantic_edges = 0
    node_list = [graph.get_node(qid) for qid in nodes_raw if graph.get_node(qid)]
    for i, a in enumerate(node_list):
        for b in node_list[i+1:]:
            if a.embedding and b.embedding:
                sim = cosine_similarity(a.embedding, b.embedding)
                if sim > 0.85:
                    graph.add_edge(a.id, b.id, weight=sim * 0.5)
                    semantic_edges += 1
                    
    logger.info("Created %d relation edges and %d semantic edges.", edges_created, semantic_edges)
    
    graph.save()
    logger.info("Database saved successfully. Graph size: %d nodes, %d edges.", len(graph.nodes), len(graph.edges))


if __name__ == "__main__":
    main()
