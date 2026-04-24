---
title: Adaptive Planning in SuperIgor
type: concept
sources:
- CrafText environment study
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Reinforcement Learning
- AI Agents
- Large Language Models
- Automated Planning
---

## TLDR

The SuperIgor agent utilizes a diverse distribution of LLM-generated plans rather than relying on a single expert path, leading to superior generalization in stochastic environments.

## Body

SuperIgor is an agent framework tested in the highly stochastic and partially observable *CrafText* environment. Unlike standard instruction-following baselines or 'Oracle' agents trained on perfect human-written plans, SuperIgor learns from a wide variety of LLM-generated plans.

By training on a diverse plan distribution rather than a single 'expert' path, the agent develops a robust internal model of the environment. This approach allows it to learn the underlying logic of the tasks instead of memorizing a single success vector. Consequently, while Oracle agents may overfit to training data, SuperIgor demonstrates superior generalization on unseen object combinations.

A critical finding from the research is that scaling Reinforcement Learning (RL) compute on a fixed, poor plan distribution eventually hits a performance ceiling. To overcome this saturation, the planner must be adaptive, continuously adjusting to the realities of the environment.

## Counterarguments / Data Gaps

While adaptive planning improves generalization, generating and processing a wide distribution of LLM plans may incur higher computational overhead during the planning phase compared to using a single fixed plan. Furthermore, in highly constrained or deterministic environments where a single optimal path exists, the overhead of learning from diverse, potentially suboptimal plans might not yield significant benefits over a standard Oracle agent.

## Related Concepts

[[Ontology-based Skill Curriculum]] [[DPO as a Grounding Signal]]

