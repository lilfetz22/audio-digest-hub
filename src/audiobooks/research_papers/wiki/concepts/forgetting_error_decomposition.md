---
title: Forgetting Error Decomposition
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Continual Learning
- Model Evaluation
---

## TLDR

A framework to quantify forgetting by splitting performance degradation into a training loss component and a generalization gap.

## Body

The authors propose a formal decomposition to understand why performance drops on old tasks. They categorize the total 'forgetting error' into two distinct sources: the training loss component and the delayed generalization gap. The former measures how much the weights no longer minimize the loss on the specific training data points of previous tasks.

The second component, the delayed generalization gap, captures how the shifted weights perform on unseen data from past tasks. This distinction is crucial because a model might still produce low loss on old training data (if the weights haven't moved too far) but show significantly worse performance on held-out test data, indicating that the network's capacity to generalize has been compromised by the task-switching process.

## Counterarguments / Data Gaps

While this decomposition provides clarity, it assumes that the training data for previous tasks remains accessible for measurement. In many real-world continual learning scenarios, access to previous data is restricted due to privacy concerns or memory constraints, making this decomposition difficult to compute in practice.

## Related Concepts

[[Generalization Gap]] [[Training Dynamics]]

