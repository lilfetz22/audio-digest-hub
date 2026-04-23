---
title: Tool Orchestration (Agentic Systems)
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- AI Engineering
- Agentic Frameworks
- System Design
---

## TLDR

LLMs should serve as an orchestration layer connecting user intent to verified, external computational backends rather than performing logic internally.

## Body

In an agentic workflow, the Large Language Model (LLM) is treated as a semantic interface rather than a calculation engine. Instead of relying on the model's internal weights to perform complex tasks like quantitative analysis, the system architecture mandates the creation of a library of 'grounding functions.' These are verified, deterministic code blocks that execute the heavy lifting.

The LLM's primary responsibility is to parse user intent and map it to the appropriate function call within this library. This separation of concerns ensures that the reasoning power of the LLM is leveraged for natural language processing, while the accuracy and reliability of the output are guaranteed by traditional, deterministic software tools.

## Counterarguments / Data Gaps

This approach introduces high latency due to multiple turns of reasoning and function calling. Additionally, it requires significant engineering overhead to maintain and document a library of tools, which may not be feasible for rapid prototyping or scenarios requiring high adaptability to novel, unforeseen tasks.

## Related Concepts

[[Function Calling]] [[Retrieval-Augmented Generation (RAG)]] [[Tool Use]]

