---
title: Bismut-Elworthy-Li Formula
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Stochastic Calculus
- Optimization
- Differential Geometry
---

## TLDR

A mathematical identity that computes gradients of expectations over diffusion paths by shifting the derivative to the probability measure, circumventing the need for direct differentiation of the objective function.

## Body

The Bismut-Elworthy-Li formula provides a way to estimate the derivative of a value function that is represented as an expectation over diffusion paths. By shifting the derivative from the integrand to the underlying probability measure (the SDE path), it eliminates the need to calculate the gradient of the objective function itself.

This is particularly powerful in optimization contexts where the objective function might be non-differentiable or otherwise difficult to differentiate. It enables the adjustment of drift in stochastic systems by leveraging path-wise information rather than point-wise gradients.

[NEW ADDITIONS]: The Bismut-Elworthy-Li formula is a powerful identity in stochastic analysis. It allows for the calculation of gradients of expectations of functionals acting on SDEs by integrating over the path space of the diffusion process. By converting a gradient estimation problem into a pure expectation estimation problem, it effectively eliminates the 'curse of differentiation' in control trajectories. This makes it an essential tool for training stochastic systems where the objective function might be non-differentiable or difficult to evaluate directly via backpropagation.

## Counterarguments / Data Gaps

While the formula circumvents the need for direct differentiation of the objective, it often introduces high variance in the estimate when implemented via Monte Carlo sampling. This variance can make the convergence of the optimization process unstable in high-dimensional settings. Additionally, the computational cost of simulating multiple paths to calculate the expectation can be prohibitive in high-dimensional settings.

## Related Concepts

[[Feynman-Kac Formula]] [[Path Integral Control]]

