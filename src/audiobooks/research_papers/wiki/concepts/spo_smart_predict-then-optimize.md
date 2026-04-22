---
title: SPO+ (Smart Predict-then-Optimize)
type: concept
sources:
- https://pyepo.readthedocs.io/
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Machine Learning
- Combinatorial Optimization
- Predict-then-Optimize
---

## TLDR

A loss function that creates a convex upper bound on decision regret to facilitate gradient-based training of predictive models in optimization pipelines.

## Body

SPO+ addresses the inherent difficulty of backpropagating through integer programming solvers, where objective functions are typically piecewise constant and gradients are zero almost everywhere. By framing the problem as minimizing decision regret—the difference between the cost of the predicted decision and the true optimal decision—SPO+ provides a surrogate loss that is both convex and differentiable.

During training, the neural network learns to map input features to objective function coefficients such that the resulting optimal decision minimizes this surrogate loss. Because the loss is a convex upper bound, optimizing it directly provides a reliable signal for gradient descent, effectively bridging the gap between machine learning predictions and combinatorial optimization results.

## Counterarguments / Data Gaps

The primary limitation of SPO+ is that it is specifically designed for linear objective functions; its effectiveness diminishes or becomes inapplicable when the underlying optimization problem is non-linear or non-convex. Furthermore, while it bounds regret, the tightness of this bound is dependent on the structure of the specific optimization problem, potentially leading to loose gradients in complex combinatorial landscapes.

## Related Concepts

[[Predict-then-Optimize]] [[Decision-Focused Learning]]

