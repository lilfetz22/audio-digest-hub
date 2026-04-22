---
title: Group Relative Policy Optimization (GRPO)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.85
categories:
- Reinforcement Learning
- Machine Unlearning
---

## TLDR

An on-policy reinforcement learning method used to selectively adjust model weights during the unlearning phase.

## Body

GRPO is utilized in this context to surgically remove specific procedural knowledge from a language model. By treating the presence of algorithmic knowledge as a target for optimization, the researchers apply GRPO to discourage the model from generating the specific, known paths for algorithms like Dijkstra’s or Strassen's.

By systematically penalizing the output of established algorithmic steps during training, the policy weights are updated to excise those 'neural pathways.' This allows researchers to isolate the model's ability to solve problems without the benefit of its pre-trained memorization of standard computer science solutions.

## Counterarguments / Data Gaps

GRPO is primarily a reinforcement learning policy optimization tool; applying it for 'unlearning' may have unintended consequences on the model's general capability. There is a risk of 'catastrophic forgetting' where the model loses unrelated functional abilities during the targeted excise of specific algorithm knowledge.

## Related Concepts

[[Policy Gradient Methods]] [[Reinforcement Learning from Human Feedback (RLHF)]]

