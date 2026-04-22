---
title: Probing Episodes
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Exploration Strategies
- Model Monitoring
---

## TLDR

A mechanism within DARLING that uses dedicated, frozen-policy episodes to perform exploratory actions for change-detection without affecting the base agent's parameters.

## Body

Probing episodes act as a safety layer for the base agent. In traditional non-stationary RL, forced exploration can inadvertently skew the data used for policy updates, leading to catastrophic forgetting or biased convergence. By freezing the base agent's internal policy, these episodes ensure that the exploratory actions taken to probe the environment's current dynamics do not influence the agent's historical data or current learning trajectory.

These episodes are computationally lightweight, requiring only 0.4 to 1.5 milliseconds per episode in practice. This efficiency allows the system to frequently check for changes without creating a significant bottleneck in the overall learning pipeline, making it suitable for high-frequency or real-time deployment.

## Counterarguments / Data Gaps

The primary drawback is the opportunity cost associated with frozen policy episodes; during a probe, the agent is not optimizing for cumulative reward, which could be sub-optimal in settings where change-detection is rarely needed but time is of the essence. Additionally, the effectiveness of the probe depends on the agent's ability to cover enough of the state space to detect deviations, which may be challenging in high-dimensional environments.

## Related Concepts

[[DARLING]] [[Exploration-Exploitation Tradeoff]]

