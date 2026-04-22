---
title: Progressive Scaling
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.85
categories:
- Machine Learning
- Training Methodology
- Scaling Laws
---

## TLDR

A methodology for training neural operators that allows for the transfer of knowledge from smaller, lower-dimensional models to larger, more complex systems.

## Body

Progressive scaling addresses the curse of dimensionality by avoiding the need to train every surrogate model from scratch. By starting with smaller system dimensions and incrementally increasing complexity, researchers can reuse learned features and weights from previous iterations.

This approach not only reduces the total computational budget required to develop agents for multiple system sizes but also ensures that smaller models serve as a foundation for larger ones. It promotes a modular design philosophy where model capacity is scaled only as necessary to capture the dynamics of the target environment.

## Counterarguments / Data Gaps

Progressive scaling can lead to 'catastrophic interference' if the transition between scales is not managed carefully, where the model loses its proficiency on the initial, simpler dynamics. Furthermore, the effectiveness of this method often depends on structural similarities between the small and large-scale systems.

## Related Concepts

[[Curriculum Learning]] [[Transfer Learning]] [[Neural Network Architecture]]

