---
title: Adaptive Reward Modulation
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.92
categories:
- Reinforcement Learning
- Training Strategy
---

## TLDR

A dynamic weighting technique for RL rewards that adjusts based on training stage and solution diversity to prevent models from gaming the system by defaulting to 'I don't know'.

## Body

The Adaptive Reward Modulator addresses the systemic risk of reward hacking by applying context-aware constraints to the IDK tag. The modulator operates on two distinct levels: stage-level and sample-level. The stage-level component delays the introduction of the IDK reward until after an initial exploration phase, ensuring the model does not take the 'easy way out' before it has truly attempted to learn hard tasks.

The sample-level component monitors the entropy and diversity of the model's reasoning trajectories. If the model exhibits high path variety, the system recognizes that the model is still in an exploratory, learning state and suppresses the IDK reward. Conversely, if the agent converges on stable (yet failing) patterns, the reward is activated to sharpen the model's boundary judgment.

## Counterarguments / Data Gaps

The mechanism introduces additional hyperparameters that require precise tuning to ensure the model does not become over-conservative or overly confident. Additionally, the reliance on diversity metrics as a proxy for learning progress can be brittle if the sampling method is biased.

## Related Concepts

[[Reward Hacking]] [[Exploration vs. Exploitation]] [[Curriculum Learning]]

