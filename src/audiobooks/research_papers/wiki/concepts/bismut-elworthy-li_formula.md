---
title: Bismut-Elworthy-Li Formula
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Stochastic Calculus
- Optimization
- Differential Geometry
---

## TLDR

A mathematical identity that allows for the computation of gradients of expectations without differentiating the underlying function.

## Body

The Bismut-Elworthy-Li formula provides a way to estimate the derivative of a value function that is represented as an expectation over diffusion paths. By shifting the derivative from the integrand to the underlying probability measure (the SDE path), it eliminates the need to calculate the gradient of the objective function itself.

This is particularly powerful in optimization contexts where the objective function might be non-differentiable or otherwise difficult to differentiate. It enables the adjustment of drift in stochastic systems by leveraging path-wise information rather than point-wise gradients.

## Counterarguments / Data Gaps

While the formula circumvents the need for direct differentiation of the objective, it often introduces high variance in the estimate when implemented via Monte Carlo sampling. This variance can make the convergence of the optimization process unstable in high-dimensional settings.

## Related Concepts

[[Feynman-Kac Formula]] [[Stochastic Differential Equations]] [[Monte Carlo Methods]]

