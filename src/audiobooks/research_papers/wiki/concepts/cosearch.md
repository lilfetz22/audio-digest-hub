---
title: CoSearch
type: concept
sources:
- 'CoSearch: Joint Training of Reasoning and Document Ranking via Reinforcement Learning
  for Agentic Search'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.99
categories:
- Artificial Intelligence
- Information Retrieval
- Reinforcement Learning
- Agentic Search
---

## TLDR

A novel framework that jointly trains a reasoning agent and a generative document ranker using reinforcement learning to overcome the limitations and bottlenecks of fixed retrieval systems.

## Body

CoSearch represents a paradigm shift in how agentic search systems are developed and optimized. Traditionally, agentic search involves a Large Language Model (LLM) that iteratively reasons, generates queries, and synthesizes answers using a static, pre-trained retrieval system. CoSearch disrupts this standard pipeline by jointly training both the reasoning component and the document ranking component simultaneously.

By leveraging Reinforcement Learning (RL), CoSearch allows the retrieval mechanism to adapt alongside the agent's reasoning processes. This joint optimization ensures that the document ranker learns to fetch information that is specifically useful for the LLM's current reasoning path, rather than relying on generalized, static retrieval metrics.

This approach directly addresses the inefficiencies found in production-grade search systems. It moves away from treating the search index as a rigid, immutable tool and instead integrates it as a dynamic, trainable partner in the agent's cognitive loop.

Recent findings explicitly demonstrate the severe bottleneck caused by traditional fixed retrieval tools. In an "oracle" experiment where the standard retrieval system was replaced with a perfect one (guaranteeing the ground-truth document at rank one), researchers observed up to a 26.8% relative F1 improvement. This highlights that even highly capable reasoning agents are functionally "blind" if their retrieval mechanisms cannot adapt to the nuances of a multi-turn reasoning path. To break this constraint, CoSearch utilizes a generative document ranker. Through joint RL optimization, the generative ranker learns to align with the agent's evolving reasoning trajectories, ensuring it can dynamically understand and fetch the context required for complex, multi-step problem solving.

Further expanding on its training methodology, CoSearch utilizes techniques such as Composite Rewards and Semantic Grouping to stabilize the joint training process. By doing so, it ensures the retriever adapts specifically to the reasoning model's needs rather than merely optimizing for general semantic similarity. Empirical evaluations demonstrate that CoSearch consistently outperforms standard fixed baselines across various question-answering (QA) benchmarks. The framework is particularly advantageous for smaller models; for example, 3B-parameter models saw the most substantial benefit, successfully closing approximately 26% of the performance gap compared to an oracle system.

## Counterarguments / Data Gaps

Jointly training both an LLM's reasoning pathways and a document ranking system via Reinforcement Learning significantly increases the computational cost and complexity of the training pipeline, introducing considerable overhead compared to off-the-shelf static retrievers. It is also prone to training instabilities such as reward hacking or catastrophic forgetting. Furthermore, RL-based joint training is highly sensitive to the design of the reward function and may suffer from mode collapse if the agent and ranker co-adapt to exploit the reward signal rather than generalizing to true reasoning tasks. Finally, tightly coupling the retrieval system to a specific reasoning model might reduce the ranker's generalizability if it is paired with a different model later or applied to other tasks.

## Related Concepts

[[Composite Reward]] [[Semantic Grouping Strategy]]

