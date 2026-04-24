---
title: Conservative Q-Learning (CQL)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Reinforcement Learning
- Offline RL
---

## TLDR

An offline reinforcement learning technique that acts as a regularizer by penalizing the values of unseen state-action pairs to prevent over-optimism.

## Body

Conservative Q-Learning (CQL) is designed to tackle the specific challenges of offline reinforcement learning, where an agent must learn from a static dataset without the ability to interact with the environment. In standard offline RL, agents often suffer from over-optimism, erroneously assigning high values to out-of-distribution or unseen states.

CQL addresses this by acting as a regularizer during the training process. It explicitly pushes down the learned values of unseen state-action pairs. This mechanism ensures the agent remains skeptical of unknown situations, leading to safer and more reliable policies when the agent is eventually deployed in the real world.

## Counterarguments / Data Gaps

By strictly pushing down the values of unseen states, CQL can become overly pessimistic. This pessimism might prevent the agent from generalizing well to mildly novel states that are actually safe and highly rewarding, potentially trapping the agent in sub-optimal, overly cautious behavioral loops.

## Related Concepts

[[Meta-Conservative Quantile Regression (M-CQR)]]

