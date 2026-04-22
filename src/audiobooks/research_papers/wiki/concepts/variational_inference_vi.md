---
title: Variational Inference (VI)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Probabilistic Machine Learning
- Optimization
- Inference
---

## TLDR

VI approximates the intractable true posterior distribution of model weights by optimizing a simpler, tractable distribution.

## Body

Because exact Bayesian inference involves computing a high-dimensional integral over all possible weight configurations—which is computationally infeasible for deep neural networks—Variational Inference is used as a surrogate approach. It frames the problem as an optimization task rather than an integration task.

In this approach, practitioners select a family of simpler distributions (e.g., Gaussians) and optimize the parameters of these distributions to minimize the divergence (usually Kullback-Leibler divergence) from the true, unknown posterior. This effectively turns the goal of posterior inference into a process of minimizing the gap between the chosen proxy and the target distribution.

## Counterarguments / Data Gaps

The primary drawback of VI is the 'approximation gap'; by choosing a simple family of distributions, the model may be unable to capture complex correlations between weights that exist in the true posterior. This can lead to underestimation of uncertainty compared to more exact methods like Markov Chain Monte Carlo (MCMC).

## Related Concepts

[[Bayesian Neural Networks]] [[Evidence Lower Bound]]

