---
title: Stub-Based Evaluation
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Software Engineering
- Benchmarking
- Research Methodology
---

## TLDR

A testing methodology that replaces live data feeds with hard-coded responses to isolate model reasoning from environmental noise.

## Body

Stub-based evaluation is a critical experimental design choice used to benchmark agent performance. By using 'stubs'—predefined, consistent responses instead of live API calls—researchers can eliminate the variance introduced by fluctuating real-world data sources like market tickers or live databases.

This isolation allows the researchers to measure the model’s ability to map intents and extract parameters without being penalized for external data errors or latency issues. It creates a controlled environment where the 'reasoning' capabilities of the agent can be evaluated against a static ground truth.

## Counterarguments / Data Gaps

The primary drawback is that stub-based evaluation ignores the 'real-world' robustness of an agent. An agent that performs perfectly with stubs may fail in production if it cannot handle malformed API responses, timeout errors, or unexpected changes in data schemas that occur in live environments.

## Related Concepts

[[Unit Testing]] [[Synthetic Data]] [[Agent Benchmarking]]

