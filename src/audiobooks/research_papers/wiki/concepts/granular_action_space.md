---
title: Granular Action Space
type: concept
sources:
- Temp-R1 Research Paper
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Agentic Reasoning
- LLM Architecture
- Prompt Engineering
---

## TLDR

A design pattern for LLM agents that replaces monolithic thought blocks with specialized, distinct internal action tokens to reduce cognitive load.

## Body

In traditional search-based agents, models often utilize a single, unstructured '<think>' token to manage planning, retrieval, and reasoning simultaneously. This leads to cognitive overload, where the model struggles to balance concurrent tasks, resulting in frequent hallucinations and loss of focus. The granular action space approach addresses this by decomposing the reasoning process into discrete, functional tokens like '<plan>', '<filter>', and '<rank>'.

By formalizing these actions, the model acts as its own orchestrator, explicitly setting goals, pruning irrelevant information, and chronologically ordering facts. This separation of concerns mirrors modular software design, allowing the model to focus its attention on one specific cognitive step at a time rather than juggling the entire problem-solving pipeline as a single stream of consciousness.

## Counterarguments / Data Gaps

Critics argue that increasing the action space can complicate the model's policy space, potentially making it harder to train or causing instability if the model misuses the specific tokens. Furthermore, there is a risk of over-segmentation, where too many granular steps introduce additional latency and overhead during the inference process.

## Related Concepts

[[Chain of Thought]] [[Tool-augmented Agents]] [[Task Decomposition]]

