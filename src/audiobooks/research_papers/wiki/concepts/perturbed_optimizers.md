---
title: Perturbed Optimizers
type: concept
sources:
- https://pyepo.readthedocs.io/
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Stochastic Optimization
- Machine Learning
---

## TLDR

A technique that stabilizes gradient estimation by adding noise to objective coefficients and averaging results over multiple samples to produce a differentiable surface.

## Body

Perturbed Optimizers (such as DPO or PFYL) operate by introducing random Gaussian noise to the objective function coefficients during the forward pass of the optimization. Instead of relying on a single discrete solution, the model considers the expected behavior of the optimizer across a neighborhood of possible inputs.

By sampling multiple perturbed objective functions and averaging the resulting optimal decisions, the jagged decision surface is transformed into a smooth, expected-value surface. This probabilistic approach effectively 'washes out' the discontinuities of the integer program, providing a well-defined gradient that the neural network can follow during the backward pass.

## Counterarguments / Data Gaps

Adding noise inherently introduces variance into the gradient estimates, which may require a larger number of samples (and thus higher computational cost) to achieve convergence. The accuracy of the gradient is also sensitive to the noise distribution and magnitude; incorrect tuning can lead to biased updates that do not reflect the true optimal structure.

## Related Concepts

[[Differentiable Black-Box]] [[SPO+]] [[Monte Carlo Methods]]

