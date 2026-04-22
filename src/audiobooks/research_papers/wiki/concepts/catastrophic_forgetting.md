---
title: Catastrophic Forgetting
type: concept
sources:
- On the Theory of Continual Learning with Gradient Descent for Neural Networks (2026)
- The Kernel Regime and Interference in Continual Learning (2026)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Continual Learning
- Neural Network Optimization
---

## TLDR

Catastrophic forgetting is the phenomenon where neural networks lose previously learned information when optimizing for new, sequential tasks due to gradient interference in the parameter space.

## Body

Catastrophic forgetting represents a fundamental challenge in artificial neural networks, occurring because standard gradient descent optimization leads to weight updates that overwrite representations optimized for previous tasks. In sequential learning scenarios, the loss landscape for Task B often conflicts with the minima found for Task A, causing the model to prioritize current error reduction at the expense of historical performance.

The paper addresses this by moving beyond empirical heuristics, such as experience replay or weight regularization, seeking a theoretical framework to explain the mechanism of interference. By analyzing the geometry of the task distribution, the authors suggest that the loss of information is not merely an optimization artifact but a structural consequence of how gradient descent traverses the parameter space.

[NEW FINDINGS] In the context of sequential learning, catastrophic forgetting is further understood by examining the 'kernel regime,' where wide networks maintain weights near their initialization. By modeling the update as a geometric movement in parameter space, researchers have demonstrated that the optimization trajectory for a new task acts as a vector that shifts the model away from the optimal weight regions of prior tasks, thereby degrading performance on those original objectives.

## Counterarguments / Data Gaps

While theoretically grounded approaches provide insight, they often rely on assumptions of linear or simplified dynamics that may not fully capture the complexity of deep, non-linear neural networks. Critics argue that these theoretical bounds may be too conservative for practical, real-world deployment where over-parameterization helps mitigate forgetting through implicit regularization. Furthermore, because recent analysis focuses on the 'kernel regime,' it remains unclear if these explicit bounds hold in deep, non-linear networks where representations evolve significantly during training and feature learning occurs, rather than just simple weight updates.

## Related Concepts

[[Gradient Descent]] [[Neural Tangent Kernel]] [[Stability Analysis]]

