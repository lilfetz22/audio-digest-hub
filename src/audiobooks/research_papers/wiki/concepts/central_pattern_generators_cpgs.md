---
title: Central Pattern Generators (CPGs)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Robotics
- Bio-inspired AI
- Control Systems
---

## TLDR

Bio-inspired, rhythmic controllers that rely on coupled neurons to create natural movement patterns for robots.

## Body

Central Pattern Generators (CPGs) are biological neural circuits that produce rhythmic outputs in the absence of rhythmic input. In the context of robotic control systems, they serve as bio-inspired paradigms designed to generate natural, rhythmic movement patterns for locomotion. The researchers tested CPGs on an 8-hinged "spider" robot to evaluate their efficacy compared to standard artificial neural networks.

Unlike traditional feed-forward networks, CPGs rely on coupled neurons to natively create these rhythmic patterns. The study found that densely connected CPGs, particularly when trained with evolutionary strategies, consistently outperformed deeper, more complex architectures in a variety of locomotion tasks, hitting an optimal "Goldilocks" zone of model complexity.

## Counterarguments / Data Gaps

While highly effective for rhythmic locomotion, CPGs can be less adaptable to highly unstructured environments or tasks requiring non-rhythmic, highly variable discrete actions when compared to generalized deep reinforcement learning approaches.

## Related Concepts

[[Multi-Layer Perceptrons (MLPs)]] [[Evolutionary Strategies (CMA-ES)]]

