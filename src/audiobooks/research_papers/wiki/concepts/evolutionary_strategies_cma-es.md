---
title: Evolutionary Strategies (CMA-ES)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Optimization
- Reinforcement Learning
- Evolutionary Algorithms
---

## TLDR

Gradient-free evolutionary strategies like CMA-ES are often more robust and easier to tune than deep reinforcement learning for tasks with low-dimensional observation spaces.

## Body

When dealing with low-dimensional observation spaces, particularly in physical hardware and control tasks, gradient-free optimization methods can outshine traditional gradient-based approaches. Evolutionary Strategies (ES), such as the Covariance Matrix Adaptation Evolution Strategy (CMA-ES), are highlighted as highly effective alternatives to Deep Reinforcement Learning (DRL).

Unlike DRL, which relies on backpropagation and can be highly sensitive to hyperparameters and reward scaling, CMA-ES searches the parameter space directly. This makes it significantly easier to tune and often more robust against the noisy, non-differentiable reward landscapes typical of physical control tasks.

The core takeaway is that practitioners should match the complexity of their optimization tool to the complexity of their observation space. Avoiding the friction and overhead of deep RL when simpler, gradient-free methods suffice leads to more reliable deployments on physical hardware.

## Counterarguments / Data Gaps

Evolutionary strategies scale poorly as the number of parameters increases, making them unsuited for high-dimensional inputs like raw pixel data or massive neural networks where deep reinforcement learning excels. They can also be highly sample-inefficient in certain simulated environments compared to modern off-policy DRL methods.

## Related Concepts

[[Deep Reinforcement Learning (DRL)]] [[Gradient-Free Optimization]] [[Structural Bias]]

