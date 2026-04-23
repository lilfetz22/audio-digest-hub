---
title: Vendi Score
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Evaluation Metrics
- Machine Learning
- Natural Language Processing
---

## TLDR

A diversity metric used to quantify the number of unique semantic clusters being explored within a generated set of outputs.

## Body

The Vendi Score acts as a quantitative measure of diversity by calculating the effective number of modes or clusters within a dataset. In the context of agentic research, it is used to evaluate whether a system is producing a broad range of unique ideas or if it is suffering from semantic convergence.

By measuring the 'breadth' of the idea space, researchers can determine the efficacy of different system topologies. A higher Vendi Score indicates that the agents are exploring distinct semantic territory rather than repeating variations of the same core concept.

## Counterarguments / Data Gaps

The Vendi Score depends heavily on the underlying embedding model used to define semantic similarity; if the embedding space is biased, the score may fail to capture true innovation. Additionally, it may over-reward noise or incoherent outputs that appear 'diverse' but lack logical substance.

## Related Concepts

[[Semantic Similarity]] [[Diversity Metrics]]

