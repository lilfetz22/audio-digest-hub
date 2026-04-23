---
title: Context-Switching Fatigue
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Human-Computer Interaction
- Cognitive Science
- Developer Productivity
---

## TLDR

A cognitive burden experienced by developers when attempting to reconstruct their mental model after navigating extensive, non-linear chat histories.

## Body

Context-switching fatigue occurs in LLM-based development environments when the sequential, linear nature of chat logs fails to capture the branching logic of an iterative problem-solving process. When users must scroll through vast amounts of tokens to recall previous decisions, their working memory is depleted, leading to decreased productivity and higher error rates.

EvoGraph mitigates this by providing a visual history graph that serves as an external memory aid. By externalizing the state transitions, the system allows the developer to offload the task of state tracking to the interface, preserving the mental model of the underlying problem across multiple experiments.

## Counterarguments / Data Gaps

While visual graphs reduce cognitive load for some, they may introduce 'interface clutter' for others, especially in long-running projects where the graph becomes overly dense or complex. Navigating a large, multi-dimensional graph might eventually cause its own form of navigational fatigue compared to a simple, familiar linear scroll.

## Related Concepts

[[External Memory]] [[Cognitive Load Theory]] [[State Management]]

