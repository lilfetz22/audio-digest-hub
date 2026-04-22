---
title: Differentiable Black-Box (DBB)
type: concept
sources:
- PyEPO library documentation
- Agrawal et al. (2019)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Differentiable Programming
- Optimization
- Neural Networks
---

## TLDR

A method that achieves differentiability in optimization solvers by interpolating the decision space to create a smooth surface for gradient flow.

## Body

Differentiable Black-Box (DBB) treats the optimization solver as a differentiable layer by approximating the solver's output through interpolation. Since standard combinatorial solvers produce discrete, non-differentiable jumps, DBB smooths these transitions.

By creating this continuous approximation, the gradient of the decision with respect to the input parameters can be calculated. This enables the integration of black-box solvers into end-to-end deep learning pipelines, where the network learns to produce objective coefficients that are sensitive to the solver's internal logic.

## Counterarguments / Data Gaps

The approximation quality depends heavily on the interpolation technique, which may introduce biases or inaccuracies if the decision space is highly complex. It also often requires additional hyperparameter tuning to ensure the smoothed surface remains faithful to the original discrete problem.

## Related Concepts

[[Implicit Differentiation]] [[Differentiable Optimization]]

