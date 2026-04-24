---
title: Centralized Training, Decentralized Execution (CTDE)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Multi-Agent Systems
- Reinforcement Learning
- System Architecture
---

## TLDR

CTDE is a multi-agent architecture where agents share global information during training but operate using only local observations during execution.

## Body

Centralized Training, Decentralized Execution (CTDE) is a paradigm used in Multi-Agent Reinforcement Learning (MARL) to bridge the gap between fully centralized and fully independent agent learning. During the centralized training phase, the learning algorithm has access to the global state, joint actions, and potentially the internal states of all agents. This shared information allows the system to develop a cohesive understanding of the environment and resolve coordination challenges.

However, during execution (inference), this global communication is severed. Agents must act decentrally, relying solely on their individual, local observations. As demonstrated in UAV grid-world tests, the CTDE variant consistently outperforms independent agent setups by enabling smoother coordination without requiring unrealistic real-time communication during deployment.

## Counterarguments / Data Gaps

The centralized training phase can suffer from scalability issues as the number of agents increases, leading to an exponentially growing joint state-action space. Furthermore, there can be a disconnect between the rich information available during training and the limited information available during execution, sometimes resulting in sub-optimal decentralized policies if the local observations are not sufficiently informative.

## Related Concepts

[[Multi-Agent Reinforcement Learning (MARL)]] [[Independent Q-Learning]]

