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

A mathematical technique that allows backpropagation through stochastic nodes by expressing random samples as deterministic functions of parameters and external noise.

## Body

Standard backpropagation cannot compute gradients through random sampling processes because the operation is inherently non-differentiable. The reparameterization trick solves this by expressing a stochastic variable (like a weight sample) as a deterministic function of its distribution's parameters and an independent noise source.

For example, if sampling from a Gaussian, rather than sampling directly, one can define the sample as the mean plus the product of the standard deviation and a random variable from a standard normal distribution. This allows gradients to flow through the deterministic operations to the parameters (mean and variance), enabling the training of BNNs with standard deep learning frameworks.

## Counterarguments / Data Gaps

This trick is specific to distributions that can be reparameterized; it is not universally applicable to all stochastic variables or probability distributions. Additionally, it can introduce high variance into gradient estimates during training, necessitating techniques like gradient clipping or variance reduction methods.

## Related Concepts

[[Variational Inference]] [[Backpropagation]]

