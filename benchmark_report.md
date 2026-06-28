# TS Engine vs. Flat RAG Benchmark Report
Generated: 2026-06-28 21:17:14
Active graph size: 485 nodes, 348 edges

| Question | Engine | Duration (s) | Nodes | Sufficiency | RAG Duration (s) | RAG Nodes |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | TS Engine | 0.03s | 5 | 0.52 | 0.00s | 0 |
| Q2 | TS Engine | 0.02s | 5 | 0.52 | 0.00s | 0 |
| Q3 | TS Engine | 0.02s | 5 | 0.52 | 0.00s | 0 |
| Q4 | TS Engine | 0.02s | 5 | 0.52 | 0.00s | 0 |
| Q5 | TS Engine | 0.02s | 5 | 0.52 | 0.00s | 0 |

## Detailed Query Comparisons

### Q1: What is the relationship between artificial intelligence and computer science?
**TS Engine Answer:**
## Graph-native synthesis (TS)
**Query:** What is the relationship between artificial intelligence and computer science?

**Grounded in retrieved nodes (no LLM):**
1. `[session:87300f40-dc25-4c39-9461-0226a06c3d1a]` (conversation,session) act=0.76 stab=0.80 score=0.65 — Session 87300f40-dc25-4c39-9461-0226a06c3d1a  Synthesis under tension: Session 7f95144f-82cb-43ac-9bcf-b232b1e2c66f (topics: conversation,session)  Session 2e13907a-9bcd-40c3-b8b2-fea7956b90b3  Synthesis under tension: Session 02a091bc-4f2d-43a9-8c33-f08581e0c104 (topics: conversation,session)  Session 1f9b5438-ffc3-41a1-ac1c-a309e28f91bc  Synthesis under tension: Session 883cc964-469d-4689-b0bc-41f53604ef48 (topics:…
2. `[Q1156402]` (reasoning) act=0.78 stab=0.80 score=0.52 — reasoning: type of thought and capacity of consciously making sense of things, applying logic, and adapting or justifying practices, institutions, and beliefs based on new or existing information
3. `[Q21198]` (comp sci,comp. sci,comp. sci.,compsci) act=0.74 stab=0.80 score=0.51 — computer science: study of computation
4. `[source:adapter:hacker_news]` (adapter,hacker_news,source) act=0.90 stab=0.95 score=0.51 — External knowledge source: hacker_news  Emerged from tension around source:adapter:hacker_news
5. `[Q120208]` (developing technologies,developing technology,emerging technologies,emerging technology) act=0.78 stab=0.80 score=0.43 — emerging technology: Technologies whose development, practical applications, or both are still largely unrealized

_Constraint: answer assembled only from graph nodes; LLM is optional fallback in pipeline._

**TS Engine Reasoning Trace:**
```
graph_native_primary
```

**Flat RAG Answer:**
Flat RAG unavailable (no embedder/LLM)

---

### Q2: How does cognitive physics relate to reasoning systems?
**TS Engine Answer:**
## Graph-native synthesis (TS)
**Query:** How does cognitive physics relate to reasoning systems?

**Grounded in retrieved nodes (no LLM):**
1. `[session:87300f40-dc25-4c39-9461-0226a06c3d1a]` (conversation,session) act=0.76 stab=0.80 score=0.60 — Session 87300f40-dc25-4c39-9461-0226a06c3d1a  Synthesis under tension: Session 7f95144f-82cb-43ac-9bcf-b232b1e2c66f (topics: conversation,session)  Session 2e13907a-9bcd-40c3-b8b2-fea7956b90b3  Synthesis under tension: Session 02a091bc-4f2d-43a9-8c33-f08581e0c104 (topics: conversation,session)  Session 1f9b5438-ffc3-41a1-ac1c-a309e28f91bc  Synthesis under tension: Session 883cc964-469d-4689-b0bc-41f53604ef48 (topics:…
2. `[source:adapter:hacker_news]` (adapter,hacker_news,source) act=0.90 stab=0.95 score=0.51 — External knowledge source: hacker_news  Emerged from tension around source:adapter:hacker_news
3. `[Q1156402]` (reasoning) act=0.78 stab=0.80 score=0.49 — reasoning: type of thought and capacity of consciously making sense of things, applying logic, and adapting or justifying practices, institutions, and beliefs based on new or existing information
4. `[Q120208]` (developing technologies,developing technology,emerging technologies,emerging technology) act=0.78 stab=0.80 score=0.43 — emerging technology: Technologies whose development, practical applications, or both are still largely unrealized
5. `[Q21198]` (comp sci,comp. sci,comp. sci.,compsci) act=0.74 stab=0.80 score=0.42 — computer science: study of computation

_Constraint: answer assembled only from graph nodes; LLM is optional fallback in pipeline._

**TS Engine Reasoning Trace:**
```
graph_native_primary
```

**Flat RAG Answer:**
Flat RAG unavailable (no embedder/LLM)

---

### Q3: Explain how emerging technologies impact engineering methodologies.
**TS Engine Answer:**
## Graph-native synthesis (TS)
**Query:** Explain how emerging technologies impact engineering methodologies.

**Grounded in retrieved nodes (no LLM):**
1. `[Q120208]` (developing technologies,developing technology,emerging technologies,emerging technology) act=0.78 stab=0.80 score=0.56 — emerging technology: Technologies whose development, practical applications, or both are still largely unrealized
2. `[session:87300f40-dc25-4c39-9461-0226a06c3d1a]` (conversation,session) act=0.76 stab=0.80 score=0.56 — Session 87300f40-dc25-4c39-9461-0226a06c3d1a  Synthesis under tension: Session 7f95144f-82cb-43ac-9bcf-b232b1e2c66f (topics: conversation,session)  Session 2e13907a-9bcd-40c3-b8b2-fea7956b90b3  Synthesis under tension: Session 02a091bc-4f2d-43a9-8c33-f08581e0c104 (topics: conversation,session)  Session 1f9b5438-ffc3-41a1-ac1c-a309e28f91bc  Synthesis under tension: Session 883cc964-469d-4689-b0bc-41f53604ef48 (topics:…
3. `[source:adapter:hacker_news]` (adapter,hacker_news,source) act=0.90 stab=0.95 score=0.51 — External knowledge source: hacker_news  Emerged from tension around source:adapter:hacker_news
4. `[Q1156402]` (reasoning) act=0.78 stab=0.80 score=0.43 — reasoning: type of thought and capacity of consciously making sense of things, applying logic, and adapting or justifying practices, institutions, and beliefs based on new or existing information
5. `[Q21198]` (comp sci,comp. sci,comp. sci.,compsci) act=0.74 stab=0.80 score=0.42 — computer science: study of computation

_Constraint: answer assembled only from graph nodes; LLM is optional fallback in pipeline._

**TS Engine Reasoning Trace:**
```
graph_native_primary
```

**Flat RAG Answer:**
Flat RAG unavailable (no embedder/LLM)

---

### Q4: What are the core differences between neural networks and rule engines?
**TS Engine Answer:**
## Graph-native synthesis (TS)
**Query:** What are the core differences between neural networks and rule engines?

**Grounded in retrieved nodes (no LLM):**
1. `[session:87300f40-dc25-4c39-9461-0226a06c3d1a]` (conversation,session) act=0.76 stab=0.80 score=0.67 — Session 87300f40-dc25-4c39-9461-0226a06c3d1a  Synthesis under tension: Session 7f95144f-82cb-43ac-9bcf-b232b1e2c66f (topics: conversation,session)  Session 2e13907a-9bcd-40c3-b8b2-fea7956b90b3  Synthesis under tension: Session 02a091bc-4f2d-43a9-8c33-f08581e0c104 (topics: conversation,session)  Session 1f9b5438-ffc3-41a1-ac1c-a309e28f91bc  Synthesis under tension: Session 883cc964-469d-4689-b0bc-41f53604ef48 (topics:…
2. `[source:adapter:hacker_news]` (adapter,hacker_news,source) act=0.90 stab=0.95 score=0.51 — External knowledge source: hacker_news  Emerged from tension around source:adapter:hacker_news
3. `[Q120208]` (developing technologies,developing technology,emerging technologies,emerging technology) act=0.78 stab=0.80 score=0.47 — emerging technology: Technologies whose development, practical applications, or both are still largely unrealized
4. `[Q1156402]` (reasoning) act=0.78 stab=0.80 score=0.47 — reasoning: type of thought and capacity of consciously making sense of things, applying logic, and adapting or justifying practices, institutions, and beliefs based on new or existing information
5. `[Q21198]` (comp sci,comp. sci,comp. sci.,compsci) act=0.74 stab=0.80 score=0.42 — computer science: study of computation

_Constraint: answer assembled only from graph nodes; LLM is optional fallback in pipeline._

**TS Engine Reasoning Trace:**
```
graph_native_primary
```

**Flat RAG Answer:**
Flat RAG unavailable (no embedder/LLM)

---

### Q5: How do autonomous loops optimize graph density over time?
**TS Engine Answer:**
## Graph-native synthesis (TS)
**Query:** How do autonomous loops optimize graph density over time?

**Grounded in retrieved nodes (no LLM):**
1. `[session:87300f40-dc25-4c39-9461-0226a06c3d1a]` (conversation,session) act=0.76 stab=0.80 score=0.68 — Session 87300f40-dc25-4c39-9461-0226a06c3d1a  Synthesis under tension: Session 7f95144f-82cb-43ac-9bcf-b232b1e2c66f (topics: conversation,session)  Session 2e13907a-9bcd-40c3-b8b2-fea7956b90b3  Synthesis under tension: Session 02a091bc-4f2d-43a9-8c33-f08581e0c104 (topics: conversation,session)  Session 1f9b5438-ffc3-41a1-ac1c-a309e28f91bc  Synthesis under tension: Session 883cc964-469d-4689-b0bc-41f53604ef48 (topics:…
2. `[source:adapter:hacker_news]` (adapter,hacker_news,source) act=0.90 stab=0.95 score=0.51 — External knowledge source: hacker_news  Emerged from tension around source:adapter:hacker_news
3. `[Q120208]` (developing technologies,developing technology,emerging technologies,emerging technology) act=0.78 stab=0.80 score=0.43 — emerging technology: Technologies whose development, practical applications, or both are still largely unrealized
4. `[Q1156402]` (reasoning) act=0.78 stab=0.80 score=0.43 — reasoning: type of thought and capacity of consciously making sense of things, applying logic, and adapting or justifying practices, institutions, and beliefs based on new or existing information
5. `[Q21198]` (comp sci,comp. sci,comp. sci.,compsci) act=0.74 stab=0.80 score=0.42 — computer science: study of computation

_Constraint: answer assembled only from graph nodes; LLM is optional fallback in pipeline._

**TS Engine Reasoning Trace:**
```
graph_native_primary
```

**Flat RAG Answer:**
Flat RAG unavailable (no embedder/LLM)

---
