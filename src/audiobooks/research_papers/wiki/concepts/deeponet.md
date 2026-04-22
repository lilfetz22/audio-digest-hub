---
title: DeepONet
type: concept
sources:
- https://doi.org/10.1038/s42256-021-00302-5
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Machine Learning
- Scientific Computing
- Neural Operators
---

## TLDR

A neural operator framework designed to learn mappings between infinite-dimensional function spaces, serving as a computationally efficient surrogate for expensive numerical solvers.

## Body

DeepONet is an architecture specifically engineered to approximate nonlinear operators. Unlike standard neural networks that map finite-dimensional inputs to outputs, DeepONet learns the functional relationship between input functions (like force or system dynamics) and output functions (like system response).

In the context of agent design, it acts as a surrogate model. By training the network offline, it captures the behavior of complex differential equations or numerical solvers. Once trained, the network provides near-instantaneous inference, allowing agents to predict system dynamics at speeds orders of magnitude faster than traditional integration methods.

[NEW INFORMATION] DeepONet is based on the universal approximation theorem for operators, which posits that a neural network can learn the mapping between functions. The architecture consists of two sub-networks: a branch net that encodes the input function at discrete sensor points and a trunk net that encodes the locations where the output function is evaluated. In the context of control systems, the model effectively 'compiles' the behavior of an expensive numerical integrator into a forward pass, bypassing the need for iterative integration steps.

## Counterarguments / Data Gaps

DeepONet performance is highly dependent on the quality and diversity of the training function space; if the deployment environment falls outside the distribution of the training data, predictions can become unreliable. Additionally, while the paper provides theoretical bounds for stability, guaranteeing these bounds in high-dimensional or highly nonlinear settings remains a significant computational and analytical challenge. [NEW INFORMATION] Furthermore, accuracy is strictly bounded by the training distribution; runtime deviations can lead to unreliable outputs and potential instability.

## Related Concepts

[[Operator Learning]] [[Surrogate Modeling]] [[Universal Approximation Theorem]]

