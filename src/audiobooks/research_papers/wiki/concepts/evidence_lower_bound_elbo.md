---
title: Evidence Lower Bound (ELBO)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Optimization
- Information Theory
- Probabilistic Machine Learning
---

## TLDR

The ELBO serves as the objective function in variational inference, balancing data-fitting accuracy against prior belief consistency.

## Body

The Evidence Lower Bound (ELBO) provides a computable objective function that allows for the optimization of variational parameters. It operates as a tug-of-war between two main components: the likelihood of the data (encouraging the model to fit the observations) and the KL divergence to a prior (encouraging the model to remain consistent with existing knowledge).

Maximizing the ELBO is mathematically equivalent to minimizing the divergence between the variational distribution and the true posterior. By optimizing this bound, researchers can train BNNs using standard gradient-based optimization methods despite the underlying complexity of Bayesian inference.

## Counterarguments / Data Gaps

The ELBO is a lower bound, meaning that the optimization can get stuck in local optima. Furthermore, the objective may be biased depending on how the complexity of the prior and the likelihood is weighted, which often requires careful hyperparameter tuning.

## Related Concepts

[[Variational Inference]] [[Bayesian Neural Networks]]

