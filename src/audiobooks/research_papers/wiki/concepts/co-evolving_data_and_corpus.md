---
title: Co-evolving Data and Corpus
type: concept
sources:
- LiteResearcher
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Synthetic Data Generation
- Reinforcement Learning
- Agent Training Environments
---

## TLDR

A training strategy where an LLM generates synthetic question-answer pairs from a seed corpus, and the original source is deleted to force the agent to actively search the remaining data.

## Body

The concept of a co-evolving data and corpus serves as an automated alternative to the labor-intensive process of manually labeling thousands of research tasks. The methodology begins with a high-quality "seed" corpus, such as Wikipedia, which is fed into a Large Language Model (LLM) to generate synthetic question-answer pairs.

A critical mechanism in this process is the intentional deletion of the exact source document from the local database after the QA pair is generated. This artificial scarcity forces the training agent to actively utilize search and browse functions across the remaining documents to deduce the answer, thereby simulating genuine research and information retrieval behavior rather than simple memorization.

To ensure the environment scales in complexity, the system continuously fetches new, real-world web pages to expand the local corpus as more tasks are generated. This creates a dynamically growing virtual world that co-evolves with the agent, providing an increasingly rich and complex dataset for the agent to navigate.

## Counterarguments / Data Gaps

Relying heavily on LLMs for synthetic task generation can introduce hallucinations or biases inherent to the base model into the training pipeline. Furthermore, deleting the exact source document might sometimes render a task impossible if the remaining corpus lacks sufficient overlapping or redundant information to deduce the answer, potentially leading to noisy, unsolvable training tasks that frustrate the learning process.

## Related Concepts

[[Retrieval-Augmented Generation (RAG)]] [[Lite High-Speed Environment]]

