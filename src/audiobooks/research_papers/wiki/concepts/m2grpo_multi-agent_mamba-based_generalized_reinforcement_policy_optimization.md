---
title: M2GRPO (Multi-agent Mamba-based Generalized Reinforcement Policy Optimization)
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Reinforcement Learning
- Multi-Agent Systems
- Robotics
---

## TLDR

A reinforcement learning framework that utilizes selective state-space models to achieve efficient, long-horizon coordination in multi-agent systems.

## Body

M2GRPO integrates state-space models—specifically the Mamba architecture—into a multi-agent reinforcement learning (MARL) framework. Unlike traditional transformer-based models that suffer from quadratic complexity, M2GRPO leverages the linear-time complexity of Mamba to process sequences, making it suitable for dynamic environments like underwater robotics.

The framework emphasizes decentralized execution, where agents are trained to make decisions based solely on local history and immediate sensor inputs. By utilizing state-based memory rather than relying on a centralized critic, the model maintains coordination stability without the computational overhead typically required during deployment.

## Counterarguments / Data Gaps

While the framework shows success in simulated environments, it may struggle with highly non-stationary environments where the local history is insufficient to infer the hidden states of other agents. Furthermore, the performance drop observed when replacing the Mamba backbone suggests a heavy reliance on the specific properties of SSMs, which might not generalize to all MARL task distributions.

## Related Concepts

[[Mamba]] [[State Space Models]] [[MAPPO]] [[MASAC]] [[Decentralized Execution]]

