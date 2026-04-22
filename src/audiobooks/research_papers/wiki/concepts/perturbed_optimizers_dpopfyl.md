---
title: Perturbed Optimizers (DPO/PFYL)
type: concept
sources:
- PyEPO library documentation
- Berthet et al. (2020)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Stochastic Optimization
- Machine Learning
- Differentiable Programming
---

## TLDR

A probabilistic approach to differentiation that smooths discontinuous decision surfaces by adding Gaussian noise and averaging across multiple samples.

## Body

Perturbed Optimizers, such as Differentiable Perturbed Optimizers (DPO) and Perturbed Fenchel-Young Losses (PFYL), introduce randomness to the objective function during the forward pass. By injecting Gaussian noise into the coefficients, the algorithm generates a distribution of potential solutions rather than a single static point.

By averaging these perturbed outcomes, the method effectively turns a jagged, piecewise constant decision surface into a smooth, expected-value surface. This allows the gradient to flow through the expectation, providing a differentiable path that reflects the underlying structure of the optimization problem.

## Counterarguments / Data Gaps

The main drawback is the computational overhead, as the method requires solving the optimization problem multiple times per iteration (Monte Carlo sampling) to approximate the expectation. This can be significantly slower than gradient-based surrogates that require only a single forward/backward pass.

## Related Concepts

[[Fenchel-Young Loss]] [[Monte Carlo Sampling]] [[Reparameterization Trick]]

