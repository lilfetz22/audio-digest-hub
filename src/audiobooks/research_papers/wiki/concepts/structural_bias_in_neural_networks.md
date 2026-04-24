---
title: Structural Bias in Neural Networks
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Neural Network Architecture
- Robotics
- Optimization
---

## TLDR

Incorporating prior knowledge into a model's architecture simplifies the optimization process compared to using standard, fully connected networks.

## Body

Structural bias involves designing a neural network's architecture to reflect the known properties of the task it needs to solve, rather than relying on a generic Multi-Layer Perceptron (MLP). By hard-coding this prior knowledge, engineers can significantly reduce the complexity of the search space the optimizer must navigate.

For example, in robotics, if a physical hardware agent requires rhythmic movements, integrating a Central Pattern Generator (CPG) directly into the architecture is more effective than expecting a standard network to learn the rhythm from scratch. This approach not only saves computational resources but also ensures more robust and predictable behaviors in physical environments.

Ultimately, adding structural constraints acts as a guiding mechanism for the optimizer. It reduces friction and prevents the model from getting stuck in suboptimal local minima, proving that simplifying the "brain" of a physical agent is often the most elegant path forward.

## Counterarguments / Data Gaps

While structural bias simplifies optimization, it can limit the model's flexibility and capacity to discover novel, unexpected solutions that human designers might not have anticipated. Incorrectly applied biases can also artificially constrain the model, preventing it from learning the optimal policy if the human-injected prior knowledge is flawed.

## Related Concepts

[[Central Pattern Generators (CPG)]] [[Parameter Impact Metric]] [[Multi-Layer Perceptrons (MLP)]]

