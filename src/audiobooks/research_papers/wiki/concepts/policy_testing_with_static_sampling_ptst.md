---
title: Policy Testing with Static Sampling (PTST)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Reinforcement Learning
- Optimization
- Statistical Learning
---

## TLDR

An asymptotically instance-optimal algorithm designed to identify optimal policies in Markov Decision Processes (MDPs) with high sample efficiency.

## Body

The PTST algorithm is designed to address the challenge of best-policy identification within the framework of Markov Decision Processes. Its primary innovation lies in its ability to achieve asymptotic instance-optimality, meaning its sample complexity scales optimally with the specific difficulty of the MDP instance rather than relying on worst-case bounds. 

By leveraging the generative model assumption—where an agent can reset the environment to any state-action pair—PTST systematically gathers data to reach a desired confidence level. This approach effectively minimizes the number of samples required to distinguish the optimal policy from suboptimal alternatives, making it highly efficient for environments where sampling is computationally or temporally expensive.

## Counterarguments / Data Gaps

The primary limitation of PTST is its reliance on a generative model, which allows for arbitrary state-action resets. This requirement makes the algorithm difficult to apply to real-world environments where reset mechanics are either non-existent, physically constrained, or dangerous.

## Related Concepts

[[Markov Decision Processes]] [[Best-Policy Identification]] [[Generative Models]]

