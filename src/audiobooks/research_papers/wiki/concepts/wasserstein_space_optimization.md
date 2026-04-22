---
title: Wasserstein Space Optimization
type: concept
sources:
- Jinniao Qiu, 'Stochastic Control Methods for Optimization'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Optimal Transport
- Stochastic Analysis
- Optimization
---

## TLDR

An approach that extends optimization techniques from Euclidean space to the space of probability measures using Wasserstein geometry.

## Body

Optimization in Wasserstein space involves moving not just single points, but entire probability distributions. This is critical for problems where the uncertainty or the distribution of the parameter space is of primary concern rather than a single point estimate.

By leveraging the geometry of probability measures, this approach allows for more nuanced optimization in high-dimensional settings where landscapes are rugged. It effectively treats the movement toward the global minimum as an evolution of a density function, which can be modeled using partial differential equations or stochastic differential equations.

## Counterarguments / Data Gaps

Computational costs in Wasserstein space are significantly higher than in Euclidean space due to the need to compute optimal transport maps or densities. Furthermore, the mathematical formulation is highly complex, which may pose challenges for integration into existing standard deep learning software stacks.

## Related Concepts

[[Wasserstein Gradient Flow]] [[Probability Measures]] [[Mean Field Games]]

