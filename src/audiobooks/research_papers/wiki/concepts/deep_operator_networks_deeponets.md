---
title: Deep Operator Networks (DeepONets)
type: concept
sources:
- Learning the Riccati solution operator for time-varying LQR via Deep Operator Networks
  (2026)
- https://doi.org/10.1038/s42256-021-00302-5
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Machine Learning
- Scientific Machine Learning
- Neural Operators
---

## TLDR

Deep Operator Networks (DeepONets) are a neural architecture class that learns mappings between infinite-dimensional function spaces using a dual-branch (branch and trunk) system to bypass traditional numerical solver iterations.

## Body

Deep Operator Networks (DeepONets) represent a paradigm shift in solving differential equations. Unlike standard neural networks that learn mappings between finite-dimensional vectors, DeepONets learn operators—mappings between infinite-dimensional function spaces. By training on a variety of system parameters, they can approximate the solution to differential equations across a range of conditions without performing expensive iterative integration.

In the context of the Riccati equation, a DeepONet can be trained to act as a surrogate solver. Once trained, the network can map the time-varying system parameters directly to the corresponding Riccati solution matrix, effectively converting a complex optimization problem into a single forward pass through the neural network.

DeepONets utilize a dual-branch architecture to learn operators that map input functions (like system parameters) to output functions (like Riccati solution trajectories). The 'Branch' network processes the discretized input function to capture high-level features, while the 'Trunk' network functions as a basis generator for the output domain, such as the time variable. The interaction between these branches allows the network to approximate non-linear operators effectively. By representing the mapping as a dot product of the branch and trunk outputs, the architecture maintains the flexibility to evaluate the output at any point in the domain, effectively acting as a universal surrogate for complex differential equations. Based on the universal approximation theorem for operators, this architecture allows the model to predict the solution of a differential equation across a continuous domain rather than merely approximating individual points, effectively serving as a functional mapping rather than a static regression model.

## Counterarguments / Data Gaps

A major challenge with DeepONets is the high volume of high-quality training data required to cover the relevant function space. Additionally, neural network approximations lack the rigorous convergence guarantees and stability proofs associated with traditional numerical integration methods, which is a significant concern for safety-critical control systems. DeepONets often suffer from high data requirements to ensure generalization across the entire function space. Furthermore, they can be computationally expensive to train compared to standard ODE solvers when the underlying function space is highly non-smooth or exhibits chaotic behavior. They can also struggle with capturing high-frequency components of the solution unless specifically engineered with appropriate activation functions or physics-informed loss constraints, and training is sensitive to the selection of collocation points in the input function space.

## Related Concepts

[[Neural Operators]] [[Fourier Neural Operators]] [[Universal Approximation Theorem]]

