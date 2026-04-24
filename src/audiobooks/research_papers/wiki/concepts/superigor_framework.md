---
title: SuperIgor Framework
type: concept
sources:
- Self-Guided Plan Extraction for Instruction-Following Tasks with Goal-Conditional
  Reinforcement Learning
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Reinforcement Learning
- Large Language Models
- Autonomous Agents
- Curriculum Learning
---

## TLDR

A co-training framework that enables a language model and a reinforcement learning agent to iteratively teach each other how to plan and execute complex tasks without hand-coded subtasks.

## Body

Training agents to follow complex, multi-step instructions in dynamic environments often suffers from the "sparse reward" problem, where the agent only receives a signal upon completing the entire task. Traditional solutions rely heavily on hand-coded subtasks or massive amounts of expert demonstrations, which scale poorly. SuperIgor addresses this by creating a self-discovering curriculum through a co-training loop between a Large Language Model (LLM) and a Reinforcement Learning (RL) agent.

The framework operates on a four-stage iterative loop. First, the LLM acts as a planner by generating a "subtask ontology," extracting potential subtasks and mapping their logical prerequisites into a structured graph. Second, the RL agent (trained via PPO) attempts to learn these policies using Skill Curriculum Learning. Third, the system validates the plans by tracking the agent's execution success and flagging consistent failures.

Finally, the framework closes the loop by fine-tuning the LLM based on the agent's performance. By enabling the planner and the actor to continuously exchange feedback, SuperIgor dynamically adapts the complexity of the tasks to the agent's current capabilities, effectively automating the curriculum generation process.

## Counterarguments / Data Gaps

While the transcript does not detail specific limitations, co-training loops between LLMs and RL agents are typically highly computationally expensive. There is also a risk of "co-adaptation" or mode collapse, where the LLM learns to generate overly simplistic plans just to maximize the agent's success rate, failing to push the agent toward solving the overarching complex task.

## Related Concepts

[[Skill Curriculum Learning]] [[Agent-Guided Direct Preference Optimization]] [[Proximal Policy Optimization (PPO)]]

