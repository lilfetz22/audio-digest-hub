---
title: Co-Evolving Evaluation
type: concept
sources:
- Forage V2
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.9
categories:
- Evaluation Metrics
- Multi-Agent Systems
- Institutional Design
---

## TLDR

An agent architecture that separates execution and evaluation into distinct roles that dynamically update task criteria as they learn.

## Body

Co-Evolving Evaluation is an institutional design approach for AI agents that splits the system into two distinct, isolated roles: a Planner (the executor) and an Evaluator (the judge). Instead of trying to make the underlying Large Language Model smarter through fine-tuning, this architecture focuses on how the agents interact and assess each other.

Unlike traditional systems that rely on a static rubric, the Evaluator dynamically defines what 'complete' means as it learns more about the data and the task domain. This co-evolution ensures that the standards for success adapt to the complexities of the real-world data being processed, rather than remaining rigidly tied to initial assumptions.

## Counterarguments / Data Gaps

Splitting roles into multiple agents significantly increases compute costs, API calls, and latency. Furthermore, allowing an Evaluator to dynamically change the definition of 'complete' might lead to moving goalposts, making benchmarking, debugging, and reproducibility highly difficult.

## Related Concepts

[[Method Isolation as Audit Separation]] [[Blank Slate Problem in AI Agents]]

