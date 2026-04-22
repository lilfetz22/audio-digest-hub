---
title: Overconfidence
type: concept
sources:
- 'Bayesian Neural Networks: An Introduction and Survey by Ethan Goan and Clinton
  Fookes'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Model Reliability
- Failure Analysis
---

## TLDR

A phenomenon where neural networks provide highly certain predictions for data outside their training distribution.

## Body

Overconfidence in neural networks occurs because standard frequentist models are optimized to find a single point estimate of weights that minimizes training loss. These models lack an internal mechanism to gauge the reliability of their output when faced with out-of-distribution (OOD) data.

In practical applications, the model essentially interprets all inputs—even those that are novel or nonsensical—through the lens of its fixed training objective. This results in the model asserting high-confidence predictions on data it has never seen, posing significant risks in safety-critical sectors like medical diagnostics or autonomous navigation.

## Counterarguments / Data Gaps

While overconfidence is a failure mode, it is sometimes argued that models are not 'confident' in a cognitive sense, but rather that their decision boundaries are ill-defined in high-dimensional space. Techniques like temperature scaling or calibration can sometimes mitigate this issue without requiring a full transition to Bayesian frameworks.

## Related Concepts

[[Bayesian Neural Networks]] [[Frequentist Neural Networks]] [[Out-of-Distribution Detection]]

