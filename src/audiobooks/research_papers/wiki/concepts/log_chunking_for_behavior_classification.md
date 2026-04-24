---
title: Log Chunking for Behavior Classification
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Machine Learning
- Natural Language Processing
- Model Evaluation
---

## TLDR

Breaking long language model logs into smaller logical units makes specific behaviors linearly separable in a lower-dimensional space.

## Body

In the context of evaluating language model outputs, "scanners" act as classifiers that attempt to draw decision boundaries between different types of behavior, such as earnest task completion versus refusal. However, raw text logs are highly chaotic and exist in a high-dimensional feature space, making direct classification across an entire log difficult.

To address this, the authors propose "chunking" the logs. By breaking long, high-dimensional sequences of tokens into smaller, logical units like reasoning traces or specific tool calls, the evaluation problem is simplified and isolated into discrete steps.

Geometrically, this chunking process projects the complex raw text into a more manageable, lower-dimensional space. In this refined space, specific behaviors (such as syntax errors or refusals) become linearly separable. This allows evaluators to map how output changes with respect to input and pinpoint exactly where an autonomous agent deviated from its intended path.

## Counterarguments / Data Gaps

While the provided text does not explicitly detail limitations, chunking inherently risks losing long-range context or the holistic intent of a prompt sequence. If the boundaries of the "logical units" are defined poorly, or if a refusal spans across multiple chunks, the resulting lower-dimensional projection might obscure the actual behavior rather than clarify it.

## Related Concepts

[[Multi-class Rubric-based Scanners]] [[Dimensionality Reduction]] [[Decision Boundaries]]

