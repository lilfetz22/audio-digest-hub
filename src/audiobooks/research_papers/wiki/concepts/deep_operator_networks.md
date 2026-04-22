---
title: Deep Operator Networks
type: concept
sources:
- Learning the Riccati solution operator for time-varying LQR via Deep Operator Networks
  (April 2026)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Machine Learning
- Scientific Machine Learning
- Numerical Analysis
---

## TLDR

A machine learning framework designed to learn continuous mappings between function spaces, offering a path to bypass traditional iterative numerical solvers.

## Body

Deep Operator Networks (DeepONets) are a class of neural network architectures designed to learn operators—mappings between function spaces—rather than just mapping points in Euclidean space. By learning the solution operator for a differential equation, the network effectively 'pre-computes' the mapping from system parameters to the optimal controller.

In the context of the Riccati equation, a DeepONet can be trained on a distribution of time-varying system parameters to predict the Riccati solution directly. Once trained, the inference time is typically orders of magnitude faster than traditional numerical integration, enabling near-instantaneous feedback control even in high-dimensional state spaces.

## Counterarguments / Data Gaps

The primary limitation is the training phase; generating sufficient, high-quality data to represent the underlying operator accurately can be extremely data-intensive. Furthermore, neural operator approximations lack the explicit error guarantees provided by classical numerical methods, which is a major concern for safety-critical control systems.

## Related Concepts

[[Neural Operators]] [[Universal Approximation Theorem]] [[Function Approximation]]

