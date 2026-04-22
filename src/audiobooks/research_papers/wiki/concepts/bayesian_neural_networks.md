---
title: Bayesian Neural Networks
type: concept
sources:
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

A neural network architecture that treats weights as probability distributions rather than point estimates to quantify uncertainty.

## Body

Bayesian Neural Networks (BNNs) shift the standard machine learning paradigm from learning fixed weights to learning probability distributions over those weights. By applying Bayesian inference, the model considers all possible weight configurations, weighted by their posterior probability given the training data. This allows the network to inherently represent uncertainty in its parameters.

During prediction, the model performs a marginalization over these weight distributions. Instead of a single deterministic output, the model provides a distribution of outputs. This mechanism enables the network to explicitly express its confidence level based on how well the input data aligns with the training data distribution.

## Counterarguments / Data Gaps

The primary barrier to BNN adoption is computational complexity, as exact Bayesian inference is intractable for deep architectures, requiring approximation techniques like Variational Inference or Monte Carlo methods that can be slow. Furthermore, defining an appropriate prior for weights is often subjective and can significantly bias results if chosen poorly.

## Related Concepts

[[Frequentist Neural Networks]] [[Variational Inference]] [[Overconfidence]]

