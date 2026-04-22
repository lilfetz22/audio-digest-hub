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

The ELBO serves as a surrogate objective function in variational inference, balancing predictive accuracy and prior consistency to enable gradient-based optimization in complex probabilistic models like BNNs.

## Body

The Evidence Lower Bound (ELBO) provides a computable objective function that allows for the optimization of variational parameters. It operates as a tug-of-war between two main components: the likelihood of the data (encouraging the model to fit the observations) and the KL divergence to a prior (encouraging the model to remain consistent with existing knowledge).

Maximizing the ELBO is mathematically equivalent to minimizing the divergence between the variational distribution and the true posterior. By optimizing this bound, researchers can train BNNs using standard gradient-based optimization methods despite the underlying complexity of Bayesian inference.

[NEW INFORMATION] In the context of training, the ELBO acts as a surrogate objective function for the marginal likelihood. It provides a structured way to balance fitting the observed data (log-likelihood) and keeping the approximate distribution close to the prior (KL divergence). By pushing the model to satisfy the ELBO, researchers can successfully train BNNs using backpropagation, despite the stochastic nature of the parameters.

## Counterarguments / Data Gaps

The ELBO is a lower bound, meaning that the optimization can get stuck in local optima. Furthermore, the objective may be biased depending on how the complexity of the prior and the likelihood is weighted, which often requires careful hyperparameter tuning. [NEW INFORMATION] The ELBO can be a loose bound; if the gap between the ELBO and the log-marginal likelihood is large, the resulting optimization may not accurately reflect the intended Bayesian goals. This 'looseness' is a primary critique in complex neural architecture optimization.

## Related Concepts

[[Variational Inference]] [[Kullback-Leibler Divergence]]

