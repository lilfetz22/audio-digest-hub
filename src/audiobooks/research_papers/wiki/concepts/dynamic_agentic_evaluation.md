---
title: Dynamic Agentic Evaluation
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.9
categories:
- Evaluation Metrics
- Agentic Workflows
- System Architecture
---

## TLDR

Evaluation mechanisms in AI workflows should be implemented as evolving agents rather than static constraints, especially when ground truth is unknown.

## Body

Traditional evaluation in software and AI relies on static benchmarks or fixed ground truths. However, in open-ended tasks where the total scope or ground truth is unknown (like discovering all products in a catalog or navigating undocumented APIs), static evaluation falls short.

Dynamic agentic evaluation solves this by using an evaluator agent that evolves alongside the executor agents. As the executors gather more data and institutionalize their successes and failures—such as logging specific API blocks into a structured "handbook"—the evaluator updates its estimates and criteria, providing a highly adaptive feedback loop.

## Counterarguments / Data Gaps

Dynamic evaluators can suffer from "grading their own homework" bias, where the evaluator and executor converge on a shared hallucination rather than objective reality. It also increases the token cost and architectural complexity of the system.

## Related Concepts

[[Institutional Knowledge Accumulation in AI Agents]] [[Physical Isolation in Multi-Agent Systems]]

