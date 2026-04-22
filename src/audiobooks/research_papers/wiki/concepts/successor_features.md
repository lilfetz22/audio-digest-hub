---
title: Successor Features
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Reinforcement Learning
- Representation Learning
---

## TLDR

A representation method in reinforcement learning that decomposes the value function into a combination of expected future state features and a reward model.

## Body

Successor features represent a state-action pair as a vector that captures the discounted sum of expected future feature occurrences. By decoupling the environment's dynamics—represented by the successor features—from the task-specific reward function, agents can generalize more effectively across tasks.

In the context of DARLING, successor features serve as a diagnostic tool. Because they encode the transitions of the environment, a significant shift in the distribution of these vectors provides a robust signal that the environmental physics or transition probabilities have changed, independent of the rewards currently being collected.

## Counterarguments / Data Gaps

Calculating and maintaining accurate successor features can be computationally expensive in complex or high-dimensional state spaces. Furthermore, the accuracy of the detection relies heavily on the quality of the learned feature representation; if the feature extractor is poorly trained, the detection mechanism may produce false positives or fail to identify meaningful environmental shifts.

## Related Concepts

[[Generalized Policy Iteration]] [[Environment Dynamics]] [[Feature Representation]]

---

### Update (2026-04-22)

Successor features represent a state-action pair as the expected discounted sum of future features encountered by an agent. By monitoring these features rather than cumulative rewards, DARLING is able to detect shifts in the underlying transition dynamics of an environment with much higher sensitivity. This is because reward signals are often delayed or noisy indicators of a structural change in the environment.

By focusing on the model parameters or successor features, the system can identify that the environment has changed as soon as the transition dynamics shift, even if the agent has not yet experienced the full impact on its reward feedback loop. This direct monitoring approach allows for more proactive adaptation compared to reactive methods that rely on monitoring reward drops or regret accumulation.

**New counterarguments:** The primary limitation of relying on successor features is the requirement for a valid feature representation of the state space. If the feature mapping is not appropriately chosen or becomes misaligned with the environment's actual transition dynamics, the detection mechanism may produce false positives or fail to identify meaningful shifts.

Furthermore, maintaining and updating successor features adds a layer of model complexity. In high-dimensional environments, approximating these features accurately can become a computational burden, potentially offsetting the speed advantages gained by the lightweight nature of the DARLING framework.

