---
title: Causal Memory Graph (Prism)
type: concept
sources:
- Prism paper
- LOCOMO benchmark
- Mem0 baseline
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Multi-Agent Systems
- Memory Management
- Artificial Intelligence
---

## TLDR

A multi-agent memory framework that tracks the provenance of knowledge to build a shared, evolving library of skills while mathematically enforcing exploration diversity.

## Body

In multi-agent systems, managing how agents share and utilize generated knowledge is a critical challenge. The **Causal Memory Graph**, implemented in a system called Prism, addresses this by mapping exactly which agent contributed a specific piece of knowledge. This provenance tracking moves away from treating memory as a flat, unorganized database, allowing the system to understand the origin and evolution of stored information.

By tagging memories with agent-attributed provenance, the system can actively measure **"exploration divergence."** This metric indicates whether agents are genuinely exploring new solution spaces or merely echoing the same retrieved memories. Utilizing this graph allows developers to mathematically enforce diversity across an agent fleet, ensuring that parallel processing translates into actual cognitive expansion rather than redundant work.

Empirical results highlight the effectiveness of this approach. On the LOCOMO conversational memory benchmark, Prism outperformed the Mem0 baseline by 31%. Furthermore, in multi-agent optimization tasks, a four-agent Prism setup achieved a 2.8x higher improvement rate compared to a single-agent baseline. This is driven by a high "knowledge reuse rate," where agents effectively bootstrap their collective intelligence by sharing a dynamic library of "how-to" skills.

## Counterarguments / Data Gaps

While causal memory graphs drastically improve multi-agent coordination, maintaining a continuously updating graph structure introduces computational and architectural overhead. In highly scaled environments with thousands of agents, the graph could become a bottleneck if not properly optimized.

Additionally, measuring "exploration divergence" assumes that divergence always correlates with task success, which might not hold true for highly constrained or convergent tasks where agents actually need to zero in on a single optimal path.

## Related Concepts

[[Exploration Divergence]] [[Knowledge Reuse]] [[Evolutionary Memory Dynamics]]

