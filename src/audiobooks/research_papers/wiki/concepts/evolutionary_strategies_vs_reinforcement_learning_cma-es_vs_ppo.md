---
title: Evolutionary Strategies vs. Reinforcement Learning (CMA-ES vs. PPO)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Reinforcement Learning
- Evolutionary Algorithms
- Machine Learning
---

## TLDR

A comparative analysis between gradient-free evolutionary algorithms (CMA-ES) and gradient-based reinforcement learning (PPO) for training robotic controllers.

## Body

The research contrasts two distinct training philosophies for robotic locomotion: Covariance Matrix Adaptation Evolution Strategy (CMA-ES), a gradient-free evolutionary strategy, and Proximal Policy Optimization (PPO), a classic gradient-based reinforcement learning algorithm.

The findings indicate that CMA-ES is remarkably efficient for this domain. Because it does not require an "actor-critic" setup—which effectively doubles the parameter count in RL methods like PPO—CMA-ES keeps the search space lean and manageable. This allowed it to handle CPGs easily and avoid the exploration traps that hindered PPO in highly constrained tasks.

## Counterarguments / Data Gaps

PPO and other gradient-based RL methods often scale much better to high-dimensional state and action spaces, where evolutionary strategies like CMA-ES might struggle with sample inefficiency and slow convergence times.

## Related Concepts

[[Central Pattern Generators (CPGs)]] [[Architectural Over-fitting Penalty]]

