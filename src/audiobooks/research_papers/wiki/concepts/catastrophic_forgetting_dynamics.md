---
title: Catastrophic Forgetting Dynamics
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Continual Learning
- Optimization Theory
---

## TLDR

The phenomenon where neural networks lose performance on previous tasks when learning new ones is governed by a strict scaling relationship between model width, sample size, and training horizon.

## Body

Catastrophic forgetting represents the tendency of artificial neural networks to overwrite the parameters learned for prior tasks when subjected to new data. The paper argues that this is not merely an architectural failure, but a manifestation of specific mathematical dynamics. Rather than relying on a single 'silver bullet' parameter, the researchers demonstrate that the preservation of past knowledge is a function of the joint coordination between network width, the volume of training data, and the number of gradient descent steps taken during training.

Central to these dynamics is the observation that as the number of sequential tasks increases, the necessary network capacity must grow to accommodate the additional information. The study highlights that the 'width' of a network provides diminishing returns; simply increasing hidden-layer size is insufficient to prevent interference between tasks if the training horizon and sample sizes are not proportionally adjusted.

## Counterarguments / Data Gaps

Critics might argue that these findings are primarily derived from specific regimes (likely convex or over-parameterized settings) that may not fully capture the behavior of modern deep, non-convex architectures. Additionally, the reliance on early stopping may be viewed as a heuristic that hinders optimal performance on the target task compared to architectural interventions like parameter isolation or rehearsal methods.

## Related Concepts

[[Catastrophic Forgetting]] [[Neural Scaling Laws]] [[Gradient Descent]]

