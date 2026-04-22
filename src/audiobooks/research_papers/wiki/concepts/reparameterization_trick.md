---
title: Reparameterization Trick
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Deep Learning
- Optimization
- Stochastic Calculus
---

## TLDR

A mathematical technique that enables gradient-based optimization in stochastic systems by expressing random samples as deterministic functions of parameters and independent noise.

## Body

Standard backpropagation cannot compute gradients through random sampling processes because the operation is inherently non-differentiable. The reparameterization trick solves this by expressing a stochastic variable (like a weight sample) as a deterministic function of its distribution's parameters and an independent noise source.

For example, if sampling from a Gaussian, rather than sampling directly, one can define the sample as the mean plus the product of the standard deviation and a random variable from a standard normal distribution. This allows gradients to flow through the deterministic operations to the parameters (mean and variance), enabling the training of BNNs with standard deep learning frameworks.

[NEW ADDITION] Training BNNs involves sampling from weight distributions, which is inherently non-differentiable and would normally prevent the use of standard backpropagation. The reparameterization trick solves this by separating the stochastic component from the model parameters. By expressing a random variable as a deterministic function of a parameter and an auxiliary noise variable (e.g., instead of sampling from N(μ, σ²), sampling from μ + σ * ε where ε ~ N(0, 1)), the gradient can flow through the parameters μ and σ. This innovation is critical for the widespread application of gradient-based optimization in variational Bayesian models.

## Counterarguments / Data Gaps

This trick is specific to distributions that can be reparameterized; it is not universally applicable to all stochastic variables or probability distributions. Additionally, it can introduce high variance into gradient estimates during training, necessitating techniques like gradient clipping or variance reduction methods. For certain other distributions used in Bayesian modeling, this trick may not be applicable, necessitating more complex gradient estimation techniques like score function estimators, which often have higher variance.

## Related Concepts

[[Variational Inference]] [[Stochastic Neural Networks]] [[Backpropagation]]

