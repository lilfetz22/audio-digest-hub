---
title: Detection-Restart Algorithms
type: concept
sources:
- 'DARLING: Detection Augmented Reinforcement Learning with Non-Stationary Guarantees'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Reinforcement Learning
- Change Point Detection
---

## TLDR

Reinforcement learning strategies that monitor for environmental shifts and reset agent knowledge or policy parameters when a change is identified.

## Body

Detection-restart algorithms provide a mechanism for agents to survive in non-stationary environments without requiring prior knowledge of when changes will occur. These algorithms typically implement a monitoring mechanism to assess the consistency of observed transitions and rewards against the agent's current model or policy.

When the agent detects a statistically significant discrepancy—implying the environment's dynamics have shifted—the algorithm triggers a restart. This clears potentially obsolete data or biased policy states, allowing the agent to begin fresh exploration in the new environment regime.

## Counterarguments / Data Gaps

Traditional detection-restart methods are often 'reactive,' meaning they only trigger a restart after performance has already significantly degraded. This lag in detection can lead to substantial regret (lost reward) before the agent successfully recalibrates to the new environment.

## Related Concepts

[[Piecewise-Stationary MDPs]] [[Regret Minimization]]

