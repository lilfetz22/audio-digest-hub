---
title: History-Dependent Lifting
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Reinforcement Learning
- Control Theory
- State Estimation
---

## TLDR

A technique that transforms partially observable control problems into fully observable ones by projecting histories of inputs and outputs into a high-dimensional space.

## Body

History-dependent lifting addresses the challenge of partial observability in control systems by mapping sequences of past observations and actions into a latent representation. By treating this augmented state as a full state vector, the algorithm essentially reconstructs the missing information necessary for decision-making.

Once the state is projected into this higher-dimensional space, the underlying problem structure shifts from a partially observable Linear Quadratic Gaussian (LQG) framework to a standard, fully observable Linear Quadratic Regulator (LQR) problem. This shift allows practitioners to bypass the complexities of hidden-state estimation and apply traditional policy gradient optimization methods directly to the lifted representation.

## Counterarguments / Data Gaps

The primary limitation is the potential for the dimensionality of the 'lifted' space to grow rapidly, which can lead to computational inefficiency or overfitting. Additionally, the approach assumes that the history is sufficient to capture all relevant latent dynamics, which may not hold in highly non-stationary or stochastic environments.

## Related Concepts

[[Partially Observable Markov Decision Processes (POMDP)]] [[Linear Quadratic Regulator (LQR)]] [[Latent State Representation]]

