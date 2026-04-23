---
title: Temp-R1
type: concept
sources:
- 'Temp-R1: A Unified Autonomous Agent for Complex Temporal KGQA via Reverse Curriculum
  Reinforcement Learning'
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.98
categories:
- Temporal Knowledge Graph Question Answering
- Reinforcement Learning
- Natural Language Processing
---

## TLDR

A unified autonomous agent framework designed to solve complex Temporal Knowledge Graph Question Answering (TKGQA) using Reverse Curriculum Reinforcement Learning.

## Body

Temp-R1 addresses the limitations of traditional, rigid TKGQA pipelines by utilizing a unified agent architecture. Rather than relying on fixed decomposer-planner-generator sequences, it employs a dynamic approach to handle multi-hop temporal queries.

The framework integrates Reverse Curriculum Reinforcement Learning to effectively train the agent on increasingly complex temporal reasoning tasks. This allows the system to filter facts by date, perform chronological ranking, and navigate complex temporal relationships more adaptively than previous generation static pipelines.

## Counterarguments / Data Gaps

The reliance on reinforcement learning can introduce instability during training, particularly in environments with sparse reward signals or highly complex knowledge graphs. Furthermore, the performance of the model may degrade if the underlying temporal knowledge graph lacks sufficient data granularity.

## Related Concepts

[[Knowledge Graphs]] [[Reverse Curriculum Reinforcement Learning]] [[Multi-hop Reasoning]]

