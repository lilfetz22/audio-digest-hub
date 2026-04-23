---
title: Boundary-Aware Policy Optimization (BAPO)
type: concept
sources:
- 'BAPO: Boundary-Aware Policy Optimization for Reliable Agentic Search'
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Reinforcement Learning
- Agentic Workflows
- LLM Reliability
---

## TLDR

A reinforcement learning training framework designed to prevent agentic hallucination by teaching models to recognize the limits of their knowledge and abstain from answering when evidence is insufficient.

## Body

Boundary-Aware Policy Optimization (BAPO) addresses the reliability gap in LLM-based agents that are fine-tuned via reinforcement learning (RL) to search the web and synthesize information. Conventional RL training often optimizes exclusively for answer correctness, which incentivizes the model to hallucinate plausible-sounding but unsupported reasoning when faced with ambiguous or insufficient data.

BAPO introduces a mechanism to calibrate the agent’s decision-making process, specifically incorporating the ability to express uncertainty or 'I don't know' as a valid, high-reward state. By formalizing these boundaries, the framework encourages the agent to prioritize evidence-backed retrieval over speculative output generation, thereby reducing the 'hallucination wall' prevalent in current agentic search workflows.

## Counterarguments / Data Gaps

A primary concern with BAPO is the risk of over-conservatism; if the reward function for 'abstaining' is improperly calibrated, agents may become risk-averse and refuse to answer queries that they are actually capable of resolving. Additionally, the effectiveness of BAPO depends heavily on the quality and diversity of the training data used to define 'insufficient evidence,' which can be difficult to curate at scale.

## Related Concepts

[[Hallucination]] [[Reinforcement Learning from Human Feedback (RLHF)]] [[Uncertainty Quantification]]

