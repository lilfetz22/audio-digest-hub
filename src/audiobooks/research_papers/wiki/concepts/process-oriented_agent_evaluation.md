---
title: Process-Oriented Agent Evaluation
type: concept
sources:
- Terry Leitch (Agentic Failure Modes Study)
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- AI Agents
- Evaluation Frameworks
- System Architecture
---

## TLDR

A paradigm shift in evaluating AI agents that prioritizes internal workflow health and logical consistency over final-answer accuracy.

## Body

Traditional agent evaluation often relies solely on the final output to determine success or failure. However, this approach ignores the internal decision-making trajectory, which can hide brittle reasoning paths or 'lucky' outcomes that do not generalize. Process-oriented evaluation treats the agentic workflow as a system to be monitored rather than a black box.

By auditing the internal state, developers can ensure that specific agents within a multi-agent system are adhering to their defined roles (e.g., critics or synthesizers) and that information flow between components is meaningful. This holistic view allows for the identification of potential points of failure before they manifest in a degraded final result.

## Counterarguments / Data Gaps

Critics of this approach argue that it introduces excessive overhead in monitoring and telemetry, which can slow down production systems. Furthermore, defining 'correct' internal process dynamics is subjective and may vary significantly by task, potentially leading to over-constrained agent behaviors.

## Related Concepts

[[Chain-of-Thought Prompting]] [[Multi-Agent Systems]] [[Process Supervision]]

