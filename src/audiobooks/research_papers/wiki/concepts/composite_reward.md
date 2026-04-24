---
title: Composite Reward
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Reinforcement Learning
- Retrieval-Augmented Generation
- Reward Modeling
---

## TLDR

A hybrid reward mechanism combining document relevance and final answer correctness to provide a cleaner training signal for rankers.

## Body

In the context of training retrieval and reasoning systems, relying solely on the final answer to reward a model creates a noisy signal. It becomes difficult to determine whether a failure occurred because the retriever fetched the wrong documents or because the reasoner failed to process the correct information.

To solve this, a Composite Reward combines two distinct signals: Relevance Feedback and Trajectory-Level Feedback. Relevance Feedback explicitly measures whether the ranker surfaced documents containing the ground-truth answer. Trajectory-Level Feedback evaluates the correctness of the final generated answer.

This hybrid approach functions similarly to curriculum learning. It initially forces the ranker to learn basic document relevance, and subsequently fine-tunes the system to optimize how those relevant documents actually contribute to the reasoning model's final answer.

## Counterarguments / Data Gaps

Relying on explicit ground-truth relevance feedback requires heavily annotated datasets, which may not be available for niche or open-ended domains. Furthermore, forcing the ranker to rely on predefined ground-truth documents might penalize the system when it finds alternative, equally valid documents that lead to the correct final answer.

## Related Concepts

[[CoSearch]] [[Trajectory-Level Feedback]] [[Curriculum Learning]]

