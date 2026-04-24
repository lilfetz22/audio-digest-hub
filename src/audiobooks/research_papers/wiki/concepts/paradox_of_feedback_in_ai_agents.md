---
title: Paradox of Feedback in AI Agents
type: concept
sources:
- Author's experiment involving 3,500 prediction markets (tested up to April 2026
  models)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.9
categories:
- Artificial Intelligence
- Machine Learning
- Behavioral Economics
---

## TLDR

Providing AI agents with historical performance feedback surprisingly degrades their trading accuracy and profitability.

## Body

In the context of AI-driven prediction markets, conventional wisdom suggests that providing agents with feedback on their past performance should enable them to learn and optimize their strategies. However, experimental data reveals a surprising 'Paradox of Feedback.'

When LLM-based agents were given data regarding their past performance, they actually performed worse and became less profitable. Instead of utilizing the historical data to refine their predictive accuracy, the models appeared to become 'confused' by the feedback, resulting in increasingly erratic and suboptimal trading behavior.

## Counterarguments / Data Gaps

This paradox might be an artifact of how the feedback was presented in the prompt rather than an inherent inability of LLMs to learn. If the feedback data was dense, unstructured, or lacked clear causal links to previous actions, it could easily overwhelm the model's attention mechanism. Models specifically fine-tuned for reinforcement learning from environmental feedback (RLHF/RLAIF) might not exhibit this degradation.

## Related Concepts

[[Complexity Penalty in AI Reasoning]]

