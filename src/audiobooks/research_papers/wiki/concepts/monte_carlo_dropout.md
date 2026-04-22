---
title: Monte Carlo Dropout
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Machine Learning
- Regularization
---

## TLDR

A technique that uses standard Dropout layers at inference time to approximate Bayesian uncertainty estimation.

## Body

Monte Carlo (MC) Dropout provides a computationally efficient way to perform Bayesian inference by keeping Dropout active during both training and testing. By performing multiple stochastic forward passes through the network with different Dropout masks, the user can generate a distribution of outputs.

The variance or spread across these different predictions serves as an estimate of the model's epistemic uncertainty. This method is highly favored in industry applications because it requires no changes to the network architecture, leveraging existing regularization components to gain insights into model reliability without the overhead of full Bayesian parameter updates.

## Counterarguments / Data Gaps

MC Dropout is an approximation rather than an exact Bayesian posterior, meaning the uncertainty estimates can be imprecise or biased depending on the dropout rate. Furthermore, running multiple forward passes during inference increases latency, which may be unacceptable for real-time systems.

## Related Concepts

[[Bayesian Neural Networks]] [[Dropout]] [[Variational Inference]]

