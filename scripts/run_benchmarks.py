#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
import json
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from BoggersTheAI.interface.runtime import RuntimeConfig, BoggersRuntime
from BoggersTheAI.core.embeddings import cosine_similarity


BENCHMARK_QUESTIONS = [
    "What is the relationship between artificial intelligence and computer science?",
    "How does cognitive physics relate to reasoning systems?",
    "Explain how emerging technologies impact engineering methodologies.",
    "What are the core differences between neural networks and rule engines?",
    "How do autonomous loops optimize graph density over time?"
]


def run_flat_rag(runtime: BoggersRuntime, query: str, k: int = 5) -> dict:
    t0 = time.time()
    embedder = getattr(runtime.graph, "_embedder", None)
    if embedder is None or runtime.local_llm is None:
        return {
            "answer": "Flat RAG unavailable (no embedder/LLM)",
            "nodes_retrieved": 0,
            "duration": time.time() - t0
        }

    try:
        query_emb = embedder.embed(query)
    except Exception:
        query_emb = []

    if not query_emb:
        # Fallback to lexical
        context_nodes = [node for node in runtime.graph.nodes.values() if not node.collapsed][:k]
    else:
        # Cosine similarity rank
        scored = []
        for node in runtime.graph.nodes.values():
            if node.collapsed or not node.embedding:
                continue
            sim = cosine_similarity(query_emb, node.embedding)
            scored.append((sim, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        context_nodes = [node for _, node in scored[:k]]

    context_text = "\n\n".join([f"Source [{node.id}]: {node.content}" for node in context_nodes])
    prompt = f"Context:\n{context_text}\n\nQuestion: {query}\nAnswer:"
    
    try:
        # Query local LLM directly without graph propagation
        answer = runtime.local_llm.embed_text(prompt) # Just a placeholder or direct call
        # Since local_llm has synthesize/generation methods:
        # Let's call runtime.local_llm.summarize_and_hypothesize or similar if available
        # Wait, local_llm has summarize_and_hypothesize(context, query) -> dict
        res = runtime.local_llm.summarize_and_hypothesize(context_text, query)
        answer = res.get("answer", "")
    except Exception as exc:
        answer = f"Error generating answer: {exc}"

    return {
        "answer": answer,
        "nodes_retrieved": len(context_nodes),
        "duration": time.time() - t0
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate TS Engine vs. flat RAG baseline.")
    parser.add_argument("--output", type=str, default="benchmark_report.md", help="Output file path")
    args = parser.parse_args()

    print("Initializing Boggers Runtime...")
    runtime = BoggersRuntime()
    
    report_lines = [
        "# TS Engine vs. Flat RAG Benchmark Report",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Active graph size: {len(runtime.graph.nodes)} nodes, {len(runtime.graph.edges)} edges",
        "",
        "| Question | Engine | Duration (s) | Nodes | Sufficiency | RAG Duration (s) | RAG Nodes |",
        "| --- | --- | --- | --- | --- | --- | --- |"
    ]
    
    detailed_sections = ["## Detailed Query Comparisons\n"]

    for idx, q in enumerate(BENCHMARK_QUESTIONS, 1):
        print(f"\n[{idx}/{len(BENCHMARK_QUESTIONS)}] Running: {q}")
        
        # 1. Run TS Engine
        t_ts0 = time.time()
        ts_res = runtime.query_processor.process_query(q)
        ts_duration = time.time() - t_ts0
        
        # 2. Run Flat RAG
        rag_res = run_flat_rag(runtime, q)
        
        # Add to summary table
        report_lines.append(
            f"| Q{idx} | TS Engine | {ts_duration:.2f}s | {len(ts_res.context)} | {ts_res.sufficiency_score:.2f} | {rag_res['duration']:.2f}s | {rag_res['nodes_retrieved']} |"
        )
        
        # Add detailed text
        detailed_sections.append(f"### Q{idx}: {q}")
        detailed_sections.append(f"**TS Engine Answer:**\n{ts_res.answer}\n")
        detailed_sections.append(f"**TS Engine Reasoning Trace:**\n```\n{ts_res.reasoning_trace}\n```\n")
        detailed_sections.append(f"**Flat RAG Answer:**\n{rag_res['answer']}\n")
        detailed_sections.append("---\n")

    full_report = "\n".join(report_lines) + "\n\n" + "\n".join(detailed_sections)
    Path(args.output).write_text(full_report, encoding="utf-8")
    print(f"\nBenchmark completed successfully! Report written to {args.output}")


if __name__ == "__main__":
    main()
