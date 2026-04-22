---
title: Smart Predict-then-Optimize (SPO+)
type: concept
sources:
- PyEPO library documentation
- Elmachtoub & Grigas (2022)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimization
- Machine Learning
- Differentiable Programming
---

## TLDR

A surrogate loss function that creates a convex upper bound on decision regret to enable gradient-based training in optimization-integrated machine learning.

## Body

SPO+ addresses the inherent difficulty of backpropagating through combinatorial solvers, where the objective function is typically piecewise constant and yields zero gradients. By defining a surrogate loss based on decision regret—the difference between the cost of the predicted decision and the true optimal decision—SPO+ provides a smooth, convex proxy.

This proxy allows neural networks to receive a meaningful learning signal during backpropagation. Unlike standard loss functions that minimize prediction error, SPO+ focuses on minimizing the downstream regret of the optimization problem, directly linking prediction accuracy to the quality of the final operational decision.

## Counterarguments / Data Gaps

The primary limitation is that SPO+ provides an upper bound rather than the exact objective, which may lead to suboptimal performance if the bound is too loose. Additionally, it requires the underlying optimization problem to be linear, limiting its applicability to broader non-linear integer programming tasks.

## Related Concepts

[[Predict-then-Optimize]] [[Decision Regret]] [[Surrogate Loss]]

