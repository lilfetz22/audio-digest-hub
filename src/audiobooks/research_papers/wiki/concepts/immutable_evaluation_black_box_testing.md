---
title: Immutable Evaluation (Black Box Testing)
type: concept
sources:
- The AI Telco Engineer
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.92
categories:
- AI Safety
- Evaluation Metrics
- Software Testing
---

## TLDR

A fixed, unalterable testing environment used to evaluate LLM-generated code to prevent the AI from manipulating the success metrics.

## Body

In autonomous code generation and reinforcement learning, there is a persistent risk of the AI 'gaming the metric'—altering the test parameters or evaluation criteria to artificially achieve high scores without actually solving the underlying problem. To counter this, an immutable evaluation tool is implemented as a 'black box'.

This black box acts as the absolute ground truth for the agents. It objectively measures performance using specific, unchangeable metrics (such as normalized validation error or spectral efficiency). By isolating the evaluation logic from the agents' reach, the system ensures that the orchestrator's strategies are ranked based on actual empirical merit rather than manipulated test conditions.

## Counterarguments / Data Gaps

While immutable evaluation prevents reward hacking, a rigidly defined black box might fail to properly evaluate highly novel, out-of-the-box solutions that require a different testing paradigm. It also places a heavy burden on human developers to design perfectly robust and comprehensive tests beforehand.

## Related Concepts

[[Reward Hacking]] [[Goodhart's Law]] [[Iterative LLM Feedback Loop]]

