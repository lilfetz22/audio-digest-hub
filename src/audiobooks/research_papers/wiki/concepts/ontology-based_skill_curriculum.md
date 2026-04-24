---
title: Ontology-based Skill Curriculum
type: concept
sources:
- CrafText environment study
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Curriculum Learning
- Knowledge Representation
- Reinforcement Learning
---

## TLDR

Structuring tasks using an ontology-based hierarchy of prerequisites is essential for providing the ordering signal needed for an agent's skill curriculum to succeed.

## Body

An Ontology-based Skill Curriculum organizes tasks into a logical hierarchy based on prerequisites. In complex environments, agents must learn foundational skills before attempting advanced, composite tasks (referred to as "Combo" tasks).

The research highlights that simply having a curriculum is insufficient if the tasks lack logical structuring. Without an ontology to define relationships and dependencies between skills, the training process loses its 'ordering signal.' When this signal is absent, the agent's performance degrades significantly, as it struggles to naturally progress from simple atomic actions to complex task execution.

Implementing an ontology ensures that the agent builds a cumulative skill set, effectively mapping out a reliable progression path that mirrors the logical dependencies of the environment.

## Counterarguments / Data Gaps

Creating a strict ontology requires significant domain expertise and manual engineering to define the hierarchy of prerequisites accurately. In highly dynamic, open-ended, or novel environments where the optimal sequence of skill acquisition is unknown, a rigid ontology might constrain the agent's ability to discover unconventional but effective learning pathways.

## Related Concepts

[[Atomic Tasks]] [[SuperIgor Agent Framework]]

