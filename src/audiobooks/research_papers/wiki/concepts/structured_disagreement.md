---
title: Structured Disagreement
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Multi-Agent Systems
- Prompt Engineering
- Quality Assurance
---

## TLDR

Utilizing multiple AI agent personas with competing incentives to critique each other's work improves overall output quality through friction.

## Body

Structured Disagreement is a technique in multi-agent systems where different AI "personas" are intentionally designed to critique and challenge one another. Rather than relying on a single model prompted to "be smart," the workflow enforces friction between agents with differing goals or evaluation criteria.

For example, one agent might be tasked with generating a hypothesis, while another is strictly incentivized to find flaws, logical gaps, or missing evidence in that hypothesis. The resulting friction acts as an automated quality control mechanism.

This adversarial or peer-review-like process mirrors human scientific collaboration. By forcing models to defend, revise, or discard claims based on peer critique, the system filters out weak arguments, hallucinations, and logical inconsistencies before the final output is produced.

## Counterarguments / Data Gaps

Implementing structured disagreement increases token usage, computational cost, and overall latency. There is also a risk of agents getting stuck in infinite debate loops if consensus mechanisms or strict turn limits are not properly engineered.

## Related Concepts

[[Automated Research Structuring]]

