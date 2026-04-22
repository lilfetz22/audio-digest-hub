---
title: Variational Inference
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Bayesian Statistics
- Optimization
---

## TLDR

An optimization-based approach to approximate complex posterior distributions in Bayesian models.

## Body

Variational Inference (VI) turns the problem of Bayesian inference into an optimization problem by choosing a simpler, tractable family of distributions and minimizing the divergence between this approximation and the true posterior. It is the go-to method for scaling Bayesian methods to neural networks where exact integration is impossible.

In the context of BNNs, the 'Mean-Field' approach is a common form of VI that assumes all weight parameters are independent. This simplifies the computation significantly, allowing practitioners to train BNNs using standard gradient-based optimization techniques, providing a balance between theoretical rigor and computational speed.

## Counterarguments / Data Gaps

The core weakness of the Mean-Field assumption is that it ignores dependencies between weights, which often leads to poor approximations of the true posterior. This is specifically linked to the observed 'variance underestimation,' where the model fails to acknowledge its own lack of knowledge, leading to over-optimistic confidence scores.

## Related Concepts

[[Bayesian Neural Networks]] [[Hamiltonian Monte Carlo]] [[Mean-Field Approximation]]

