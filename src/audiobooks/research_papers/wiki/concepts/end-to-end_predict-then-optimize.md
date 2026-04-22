---
title: End-to-End Predict-then-Optimize
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Machine Learning
- Optimization
- Operations Research
---

## TLDR

A paradigm that integrates prediction and optimization into a single training loop to directly minimize downstream decision regret.

## Body

Traditional approaches often utilize a two-stage process where a predictive model is trained to minimize prediction error (e.g., MSE), followed by a separate optimization step using those predictions. End-to-end training, as implemented in frameworks like PyEPO, shifts this focus by incorporating the optimization task directly into the training loss function.

By differentiating through the optimization process or using surrogate gradients, the predictive model is forced to prioritize learning features that yield better decision outcomes rather than purely accurate point estimates. This alignment ensures that the model learns to ignore noise in the input data that is irrelevant to the final objective function.

## Counterarguments / Data Gaps

Directly optimizing for downstream decisions can sometimes lead to instability during training, as the loss landscape of optimization problems is often non-convex or discontinuous. Furthermore, if the underlying optimization problem is poorly defined or the predictive model has high bias, this approach may fail to converge compared to traditional supervised learning.

## Related Concepts

[[Regret Minimization]] [[Predict-then-Optimize]] [[Differentiable Optimization]]

