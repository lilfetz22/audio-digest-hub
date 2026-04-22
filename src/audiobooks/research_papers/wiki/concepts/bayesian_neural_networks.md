---
title: Bayesian Neural Networks
type: concept
sources:
- https://doi.org/10.1007/s10462-019-09756-3
- 'Bayesian Neural Networks: An Introduction and Survey by Ethan Goan and Clinton
  Fookes'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Machine Learning
- Bayesian Inference
- Uncertainty Quantification
---

## TLDR

A probabilistic approach to neural networks that treats weights as distributions rather than fixed values to enable inherent uncertainty quantification.

## Body

Bayesian Neural Networks (BNNs) shift the standard machine learning paradigm from learning fixed weights to learning probability distributions over those weights. By applying Bayesian inference, the model considers all possible weight configurations, weighted by their posterior probability given the training data. This allows the network to inherently represent uncertainty in its parameters.

During prediction, the model performs a marginalization over these weight distributions. Instead of a single deterministic output, the model provides a distribution of outputs. This mechanism enables the network to explicitly express its confidence level based on how well the input data aligns with the training data distribution.

[ADDITIONAL RESEARCH]: BNNs replace the deterministic point estimates used in standard neural networks with probability distributions over the weights. Instead of arriving at a single set of optimal parameters during training, BNNs learn a posterior distribution of weights given the training data, capturing the uncertainty associated with its internal representations. During inference, instead of performing a single forward pass, the model integrates over the weight distribution. This effectively acts as an ensemble of infinite models, allowing the network to provide both a prediction and a measure of confidence. When the input data deviates significantly from the training distribution, the posterior variance typically increases, signaling to the user that the model's prediction is unreliable.

## Counterarguments / Data Gaps

The primary barrier to BNN adoption is computational complexity, as exact Bayesian inference is intractable for deep architectures, requiring approximation techniques like Variational Inference or Monte Carlo methods that can be slow. Furthermore, defining an appropriate prior for weights is often subjective and can significantly bias results if chosen poorly. [ADDITIONAL RESEARCH]: The primary barrier is high computational cost; performing exact Bayesian inference on high-dimensional weight spaces is analytically intractable. While variational inference and Monte Carlo methods offer approximations, they often require significant memory overhead and increased latency during both training and inference compared to standard deep learning architectures.

## Related Concepts

[[Variational Inference]] [[Uncertainty Estimation]] [[Frequentist Neural Networks]] [[Overfitting]]

