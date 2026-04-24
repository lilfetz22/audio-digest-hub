---
title: Skill Curriculum Learning
type: concept
sources:
- Self-Guided Plan Extraction for Instruction-Following Tasks with Goal-Conditional
  Reinforcement Learning
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.92
categories:
- Reinforcement Learning
- Curriculum Learning
- Autonomous Agents
---

## TLDR

An RL training approach where an agent masters simple, single-subtask plans before progressing to more complex, multi-step chains to overcome sparse rewards.

## Body

In environments characterized by sparse rewards, agents struggle to randomly stumble upon the exact sequence of actions required to complete a complex task. Skill Curriculum Learning mitigates this by breaking the overarching task into a logical progression of smaller, manageable subtasks based on a generated ontology.

The agent begins its training focused entirely on isolated, simple subtasks. The system establishes a specific success threshold for these basic actions. Once the agent consistently meets or exceeds this threshold, the subtask is officially marked as "mastered." 

Following the mastery of individual foundational skills, the curriculum gradually introduces slightly more complex chains of subtasks. This step-by-step scaling allows the agent to build up to fulfilling the entire complex instruction, leveraging previously learned policies rather than attempting to learn a massive sequence of actions from scratch.

## Counterarguments / Data Gaps

Defining the "success threshold" for mastery can be arbitrary and requires careful tuning; too low, and the agent fails at complex chains; too high, and training stalls. Additionally, mastering isolated skills does not guarantee they can be smoothly chained together, as compounding errors or context shifting between subtasks often introduce new modes of failure.

## Related Concepts

[[SuperIgor Framework]] [[Subtask Ontology]] [[Proximal Policy Optimization (PPO)]]

