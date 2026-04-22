---
title: Catastrophic Forgetting in the Kernel Regime
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Machine Learning Theory
- Continual Learning
- Neural Dynamics
---

## TLDR

The phenomenon where neural networks lose performance on previous tasks when trained sequentially, analyzed here within the mathematical constraints of the kernel regime.

## Body

Catastrophic forgetting occurs when a model's parameters are updated to minimize loss on a new task, effectively overwriting the representations previously learned for earlier tasks. By focusing on a wide, one-hidden-layer neural network, the authors operate in the 'kernel regime,' where weights remain close to their initialization. This allows for a linear approximation of the network's behavior, making the dynamics of forgetting mathematically tractable.

The authors decompose the forgetting error into two distinct parts: the training loss component, which measures how much the model fails to satisfy the original training data of past tasks after parameter updates, and the delayed generalization gap, which quantifies the drop in performance on unseen test data from those same previous tasks. This framework transforms the study of forgetting from an empirical observation into a quantifiable geometric problem within parameter space.

## Counterarguments / Data Gaps

The primary limitation is the focus on the 'kernel regime,' where wide networks exhibit limited feature learning. In modern deep learning, representation learning is a core component of task success, and results derived from static kernels may not fully capture the complex dynamics of deep, feature-learning architectures.

Additionally, the assumption of orthogonal tasks simplifies the problem significantly. Real-world tasks are rarely orthogonal and often share hierarchical or overlapping features, which can either mitigate or exacerbate interference in ways that this specific setup does not account for.

## Related Concepts

[[Neural Tangent Kernel (NTK)]] [[Catastrophic Forgetting]] [[Continual Learning]] [[Gradient Descent]]

