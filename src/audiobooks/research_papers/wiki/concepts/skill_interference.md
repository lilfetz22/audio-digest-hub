---
title: Skill Interference
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Machine Learning
- Agentic Systems
- Lifelong Learning
---

## TLDR

A phenomenon where the addition of new capabilities to an agent's library degrades its performance on previously mastered tasks.

## Body

Skill interference occurs when the integration of new data or behavioral patterns within an agent's policy leads to the corruption or overwriting of existing functional pathways. As the agent attempts to incorporate new skills, the underlying optimization process may cause the model to shift away from previously discovered optimal weights or logic flows.

In the context of agentic architectures, this often manifests as a decline in performance despite the agent having access to a wider repository of tools. It represents a failure in parameter management where the model's 'skill library' becomes bloated or misaligned, leading to contradictory behaviors when executing multi-step tasks.

## Counterarguments / Data Gaps

Critics argue that skill interference may be a byproduct of suboptimal indexing or retrieval mechanisms rather than inherent corruption of the model's logic. If the retrieval system fails to precisely trigger the relevant skill, it may induce noise that mimics the appearance of performance regression.

## Related Concepts

[[Catastrophic Forgetting]] [[Utility Gap]]

