---
title: L2 Regularization Equivalency
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Optimization Theory
- Regularization
---

## TLDR

In the context of continual learning, standard L2 regularization is mathematically equivalent to step-size rescaling and fails to fundamentally alter forgetting dynamics.

## Body

The research suggests that the widely used L2 regularization—often employed to prevent overfitting—is less effective at mitigating forgetting than its popularity suggests. By analyzing the weight decay dynamics, the authors prove that L2 regularization essentially functions as a rescaling of the gradient descent step size in this specific regime.

Because this regularization does not fundamentally alter the optimization trajectory in a way that preserves past representations, it fails to solve the root cause of task interference. Practitioners often rely on L2 as a default tool, but this finding indicates that it does not provide the structural protection needed to maintain model performance across long sequences of tasks.

## Counterarguments / Data Gaps

While L2 may be mathematically equivalent to step-size rescaling in specific theoretical constraints, empirical evidence in non-linear deep learning often shows that L2 regularization can still improve generalization and stability by smoothing the loss landscape. Disputing this finding would involve examining if these results hold for non-convex loss functions where weight decay might interact with optimization differently than in linear settings.

## Related Concepts

[[Weight Decay]] [[Overfitting]] [[Gradient Descent]]

