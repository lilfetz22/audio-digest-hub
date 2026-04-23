---
title: Group Relative Policy Optimization (GRPO)
type: concept
sources:
- DeepSeek-R1 Technical Report
created: '2026-04-22'
updated: '2026-04-23'
confidence: 0.92
categories:
- Reinforcement Learning
- Machine Unlearning
---

## TLDR

A reinforcement learning optimization technique that enhances reasoning by evaluating groups of model outputs to reinforce superior action sequences, while also being applied for targeted machine unlearning.

## Body

## Existing Context
GRPO is utilized in this context to surgically remove specific procedural knowledge from a language model. By treating the presence of algorithmic knowledge as a target for optimization, the researchers apply GRPO to discourage the model from generating the specific, known paths for algorithms like Dijkstra’s or Strassen's.

By systematically penalizing the output of established algorithmic steps during training, the policy weights are updated to excise those 'neural pathways.' This allows researchers to isolate the model's ability to solve problems without the benefit of its pre-trained memorization of standard computer science solutions.

## New Research Findings
Group Relative Policy Optimization (GRPO) functions by evaluating a group of policy outputs to determine which action sequences are superior relative to the group average. This approach moves beyond simple supervised fine-tuning by allowing the model to explore and reinforce specific pathways within its latent space.

By forcing the model to carve out stable, distinct pathways, GRPO ensures that the agent maps specific query types to coherent logical steps. This structural rigor helps the model avoid the tendency to guess or hallucinate, as it is actively rewarded for selecting the most effective action sequence for a given task.

## Counterarguments / Data Gaps

GRPO is primarily a reinforcement learning policy optimization tool; applying it for 'unlearning' may have unintended consequences on the model's general capability, such as 'catastrophic forgetting' where the model loses unrelated functional abilities. Additionally, GRPO can be computationally expensive to generate and evaluate groups of outputs during the training process, and there is a significant risk of reward hacking if the evaluation criteria for 'optimal' actions are not perfectly aligned with the desired model behavior.

## Related Concepts

[[Policy Gradient Methods]] [[Latent Space Mapping]] [[Reasoning Chains]]

