---
title: Catastrophic Forgetting
type: concept
sources:
- On the Theory of Continual Learning with Gradient Descent for Neural Networks (2026)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Continual Learning
- Neural Network Optimization
---

## TLDR

The phenomenon where neural networks lose previously learned information when trained on new, sequential tasks.

## Body

Catastrophic forgetting represents a fundamental challenge in artificial neural networks, occurring because standard gradient descent optimization leads to weight updates that overwrite representations optimized for previous tasks. In sequential learning scenarios, the loss landscape for Task B often conflicts with the minima found for Task A, causing the model to prioritize current error reduction at the expense of historical performance.

The paper addresses this by moving beyond empirical heuristics, such as experience replay or weight regularization, seeking a theoretical framework to explain the mechanism of interference. By analyzing the geometry of the task distribution, the authors suggest that the loss of information is not merely an optimization artifact but a structural consequence of how gradient descent traverses the parameter space.

## Counterarguments / Data Gaps

While theoretically grounded approaches provide insight, they often rely on assumptions of linear or simplified dynamics that may not fully capture the complexity of deep, non-linear neural networks. Critics argue that these theoretical bounds may be too conservative for practical, real-world deployment where over-parameterization helps mitigate forgetting through implicit regularization.

## Related Concepts

[[Gradient Descent]] [[Multitask Learning]] [[Catastrophic Interference]]

