---
title: Group-Relative Policy Optimization (GRPO)
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Reinforcement Learning
- Optimization
---

## TLDR

A reinforcement learning training scheme that eliminates the need for a centralized value critic by normalizing rewards across agent groups.

## Body

GRPO is an optimization strategy adapted for the multi-agent reinforcement learning (MARL) setting. Traditional MARL approaches typically require a centralized critic network to estimate state-action values, which introduces substantial memory consumption and complexity during training. GRPO circumvents this requirement by utilizing relative advantages.

In this scheme, rewards are normalized across a group of parallel environments. By calculating each agent's performance advantage relative to the mean performance of the group, the algorithm filters out environmental noise. This normalization provides a stable, unbiased signal for policy updates, allowing for effective optimization without the memory-intensive overhead of maintaining an explicit value function.

## Counterarguments / Data Gaps

The reliance on group-relative normalization assumes that parallel environments or agent groups are sufficiently similar to provide a meaningful baseline; if high variance exists between environmental instances, the advantage estimates may become unstable. Additionally, it may fail to capture complex, non-linear dependencies that a deep centralized critic would otherwise learn.

## Related Concepts

[[Multi-Agent Reinforcement Learning]] [[Policy Gradient Methods]]

