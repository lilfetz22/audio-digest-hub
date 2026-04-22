---
title: Successor Features
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Reinforcement Learning
- Representation Learning
---

## TLDR

A reinforcement learning representation technique that decomposes the value function to decouple environmental dynamics from rewards, allowing for proactive, non-stationarity detection.

## Body

Successor features represent a state-action pair as a vector that captures the discounted sum of expected future feature occurrences. By decoupling the environment's dynamics—represented by the successor features—from the task-specific reward function, agents can generalize more effectively across tasks.

In the context of DARLING, successor features serve as a diagnostic tool. Because they encode the transitions of the environment, a significant shift in the distribution of these vectors provides a robust signal that the environmental physics or transition probabilities have changed, independent of the rewards currently being collected. 

Successor features represent a state-action pair as the expected discounted sum of future features encountered by an agent. By monitoring these features rather than cumulative rewards, DARLING is able to detect shifts in the underlying transition dynamics of an environment with much higher sensitivity. This is because reward signals are often delayed or noisy indicators of a structural change in the environment. By focusing on the model parameters or successor features, the system can identify that the environment has changed as soon as the transition dynamics shift, even if the agent has not yet experienced the full impact on its reward feedback loop. This direct monitoring approach allows for more proactive adaptation compared to reactive methods that rely on monitoring reward drops or regret accumulation. 

[NEW ADDITION] Successor Features provide a framework for decomposing the value function in reinforcement learning by separating the dynamics of the environment from the reward function. By monitoring the average of these feature vectors after a transition, the system creates a signature of the environmental dynamics. If the transition physics or the structure of the state space changes, the distribution of these features shifts, allowing for the detection of non-stationarity independent of the specific task rewards.

## Counterarguments / Data Gaps

Calculating and maintaining accurate successor features can be computationally expensive in complex or high-dimensional state spaces. Furthermore, the accuracy of the detection relies heavily on the quality of the learned feature representation; if the feature extractor is poorly trained, the detection mechanism may produce false positives or fail to identify meaningful environmental shifts. Additionally, the requirement for a valid feature representation means that if the mapping is not appropriately chosen or becomes misaligned with the environment's actual transition dynamics, the detection mechanism may fail to identify subtle but critical environmental shifts.

## Related Concepts

[[Successor Representations]] [[State Space Models]]

