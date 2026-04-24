---
title: Group Relative Agent Optimization (GRAO)
type: concept
sources:
- TPGO (Implied from text)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Meta-learning
- Few-shot Prompting
- Memory Systems
- Optimization
---

## TLDR

A meta-learning layer that uses an Optimization Experience Memory to retrieve past failures and successful fixes for few-shot prompt optimization.

## Body

Group Relative Agent Optimization (GRAO) acts as a meta-learning layer within the TPGO framework. Instead of relying on the optimizer to blindly guess how to fix a diagnosed bug, GRAO leverages historical data to inform and guide its corrections.

It achieves this by maintaining an "Optimization Experience Memory." When the system encounters a new failure, it searches this memory to retrieve past, similar failures along with the specific fixes that successfully resolved them in previous iterations.

These retrieved historical examples are then used as few-shot prompts to "prime" the optimizer. This contextual grounding enables the optimizer to generate a much more accurate, targeted, and effective fix for the current issue based on proven past experiences.

## Counterarguments / Data Gaps

Maintaining and querying an Optimization Experience Memory requires additional storage and compute resources, potentially slowing down the optimization cycle. Furthermore, if the memory becomes polluted with suboptimal fixes or if retrieved examples are incorrectly matched to the current context, it could lead to negative transfer and actually degrade the agent's performance.

## Related Concepts

[[Textual Parameter Graph (TPG)]] [[Textual Gradients]]

