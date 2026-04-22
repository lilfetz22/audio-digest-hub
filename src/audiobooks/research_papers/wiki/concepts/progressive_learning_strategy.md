---
title: Progressive Learning Strategy
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Deep Learning
- Transfer Learning
- Scaling Laws
---

## TLDR

A transfer learning technique that freezes core operator layers to allow scaling to higher-dimensional systems by only training auxiliary embedding and lifting layers.

## Body

The Progressive Learning Strategy addresses the challenge of scaling neural operators to high-dimensional state spaces. By leveraging the pre-trained weights of a base operator trained on smaller systems, the model retains fundamental physical insights regarding the structure of the differential equations.

During scaling, the system employs 'lifting' layers to map higher-dimensional inputs into the previously established latent space and 'embedding' layers to interpret the output. This modular approach minimizes catastrophic forgetting and significantly reduces the computational burden and data requirements compared to training a new model from scratch.

## Counterarguments / Data Gaps

This strategy assumes a degree of structural similarity between the low-dimensional and high-dimensional systems. If the system dynamics change qualitatively as dimensions increase, the frozen base operator may act as an inductive bias that limits the model's ability to learn new, non-transferable behaviors.

## Related Concepts

[[Amortized Inference]] [[Transfer Learning]] [[Domain Adaptation]]

