---
title: Capability Gaps in Transformers
type: concept
sources:
- 'NeuroAI and Beyond: Bridging Between Advances in Neuroscience and Artificial Intelligence
  (2025 NSF Workshop)'
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.9
categories:
- Machine Learning
- Transformer Architectures
---

## TLDR

The identified limitations of current transformer models, specifically regarding physical interaction, continuous learning, and energy efficiency.

## Body

The current generation of large language models is built upon static training methodologies where data is 'frozen in time.' This architectural constraint results in a 'passive observer' paradigm, where models cannot update their knowledge base in real-time or learn from new environmental experiences, leading to significant performance gaps in embodied, physical tasks.

Furthermore, the current scaling law trajectory prioritizes compute power over architectural ingenuity, resulting in systems that are fundamentally inefficient. While transformers excel at sequence completion, they lack the causal reasoning required to predict outcomes in unpredictable, physical environments, which are essential for real-world robotics and autonomous systems.

## Counterarguments / Data Gaps

Some researchers argue that 'scaling' is not yet exhausted and that multi-modal models (combining vision, audio, and language) can eventually bridge these gaps without needing a fundamental shift in architecture. Others point to 'World Models' within LLMs as an emerging capability that might provide enough causal grounding to handle simple physical interaction without replacing the transformer backbone.

## Related Concepts

[[Large Language Models]] [[Embodied AI]] [[Causal Inference]]

