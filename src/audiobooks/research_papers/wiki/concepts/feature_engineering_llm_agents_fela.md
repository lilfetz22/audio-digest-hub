---
title: Feature Engineering LLM Agents (FELA)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Artificial Intelligence
- Machine Learning
- Automated Feature Engineering
- Multi-Agent Systems
---

## TLDR

FELA is a multi-agent system that automates feature engineering by simulating a human research team to generate, code, and review data features.

## Body

FELA (Feature Engineering LLM Agents) operates as a collaborative, multi-agent system designed to automate the feature engineering process. Rather than simply using a Large Language Model (LLM) as a static code generator, FELA treats the AI as a dynamic team of researchers capable of proposing hypotheses, writing code, and peer-reviewing outputs.

The framework relies on a specialized team of agents to accomplish this workflow. **Idea Agents** are responsible for generating abstract, human-readable hypotheses about the data (e.g., "users who buy complementary items are more loyal"). **Code Agents** translate these conceptual insights into concrete Python code. Finally, **Critic Agents** serve as a peer-review mechanism, validating syntactic correctness and logical soundness before any code is executed against production data.

To bridge the gap between abstract thought and concrete implementation, FELA utilizes a two-layer **Hierarchical Knowledge** structure. It explicitly separates *Ideas* (the abstract insights) from *Features* (the executable code). This hierarchical organization allows the system to iterate on various code realizations without losing track of the foundational hypothesis.

## Counterarguments / Data Gaps

While FELA automates complex data science workflows, multi-agent LLM systems often suffer from high computational overhead, latency, and API costs. Furthermore, automated Critic Agents may not catch subtle semantic errors, data leakage, or edge-case bugs, meaning human oversight is often still required. The quality of the generated features is also heavily bottlenecked by the underlying LLM's domain knowledge and reasoning capabilities.

## Related Concepts

[[Agentic Evolution]] [[Large Language Models]] [[Automated Machine Learning (AutoML)]]

