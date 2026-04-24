---
title: Agent-Guided Direct Preference Optimization (DPO)
type: concept
sources:
- Self-Guided Plan Extraction for Instruction-Following Tasks with Goal-Conditional
  Reinforcement Learning
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Large Language Models
- Model Fine-Tuning
- Reinforcement Learning
---

## TLDR

A method of fine-tuning language models where an RL agent's actual physical or simulated execution success rate serves as the preference signal for the LLM's generated plans.

## Body

Direct Preference Optimization (DPO) is traditionally used to align language models with human preferences by providing pairs of chosen and rejected responses. In the context of agentic planning, this concept is adapted to use the reinforcement learning agent's actual success rate as the ground-truth preference signal. 

Instead of relying on human heuristics or generic reward models to evaluate a plan's quality, the system monitors which generated plans the agent successfully executes and which ones it consistently fails. The LLM is then fine-tuned via DPO to prioritize the types of plans, structures, and sequences that the agent finds easier to execute.

This creates a highly grounded feedback mechanism. The LLM ceases to be an abstract planner and instead becomes highly tailored to the specific mechanical and cognitive capabilities (or limitations) of the RL agent it is guiding, ensuring that generated task graphs are actually actionable.

## Counterarguments / Data Gaps

Basing DPO strictly on an agent's success rate assumes that failure is always a result of poor planning, which ignores failures caused by the agent's lack of physical capability or random environmental noise. Furthermore, if the agent is weak, this feedback mechanism might strictly penalize complex plans, preventing the LLM from generating the sophisticated strategies required for advanced tasks.

## Related Concepts

[[SuperIgor Framework]] [[Direct Preference Optimization (DPO)]] [[Reinforcement Learning from Human Feedback (RLHF)]]

