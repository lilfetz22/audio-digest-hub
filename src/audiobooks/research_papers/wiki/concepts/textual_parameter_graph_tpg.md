---
title: Textual Parameter Graph (TPG)
type: concept
sources:
- TPGO (Implied from text)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Agentic Systems
- Prompt Engineering
- Graph Modeling
- System Optimization
---

## TLDR

A framework that models complex LLM agent systems as directed graphs with modular semantic nodes and edges to enable targeted optimization.

## Body

TPGO models an agent system as a Textual Parameter Graph (TPG) rather than a monolithic block of text. This directed graph structure consists of nodes representing modular semantic units, specifically Role nodes (personas), Logic nodes (reasoning protocols), and Tool nodes (API specifications).

The edges within the TPG represent the dependencies and information flow between these modular units. By mapping the system in this way, optimization transforms into a process of graph evolution rather than complete prompt rewriting.

Instead of rewriting an entire prompt when an error occurs, the system can perform targeted, surgical modifications. This includes rewriting individual Tool nodes, pruning faulty edges between agents, or adding new Logic nodes to bridge identified reasoning gaps.

## Counterarguments / Data Gaps

While modeling agent systems as graphs enables surgical optimization, it may introduce significant overhead in parsing and maintaining the graph structure, especially for highly dynamic or unstructured agent interactions. Furthermore, rigidly defining nodes as Role, Logic, or Tool might constrain more fluid or hybrid agent behaviors that do not fit neatly into these categories.

## Related Concepts

[[Textual Gradients]] [[Group Relative Agent Optimization (GRAO)]]

