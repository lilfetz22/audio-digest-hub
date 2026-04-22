---
title: DARLING (Detection Augmented Reinforcement Learning)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Reinforcement Learning
- Non-stationary Environments
- Model Adaptation
---

## TLDR

A modular framework that enhances stationary RL algorithms by using periodic state-action probes to detect environmental changes and trigger model resets.

## Body

DARLING functions as a wrapper for standard reinforcement learning agents, effectively transforming them into non-stationary environment handlers. It operates on the principle of active monitoring rather than passive observation. By requiring the agent to periodically revisit a specific set of state-action 'probes,' the framework continuously collects data points that act as a baseline for environmental stability.

Technically, the system tracks two primary data streams: reward histories and successor feature transitions. By mapping state-action pairs into a high-dimensional feature space, DARLING can detect drift in the underlying environment dynamics. When a Generalized Detection Test determines that the statistical properties of these streams have shifted beyond a pre-defined threshold, the framework identifies a non-stationary event.

Upon detection of an environment shift, DARLING executes a 'restart' mechanism. This process clears the base learner's internal memory or accumulated statistics, forcing the agent to adapt to the new transition dynamics or reward structure by re-learning from scratch, thereby avoiding the interference of outdated environmental knowledge.

## Counterarguments / Data Gaps

A primary limitation of DARLING is the efficiency loss caused by the 'probe' requirement; forcing an agent to visit specific state-action pairs may significantly degrade performance in environments where exploration is costly or dangerous. Additionally, the 'clear memory' approach is a blunt instrument that discards potentially useful information that could have been transferred across environments if more sophisticated continual learning techniques were employed.

## Related Concepts

[[Successor Features]] [[Generalized Detection Test]] [[Continual Learning]] [[Change Point Detection]]

