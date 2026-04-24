---
title: Architectural Over-fitting Penalty
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.92
categories:
- Deep Learning
- Model Architecture
- Robotics
---

## TLDR

The phenomenon where massive, over-parameterized networks fail to learn efficiently in constrained tasks compared to simpler, shallow architectures.

## Body

The study reveals a "Goldilocks" zone for robotic controllers where shallow Multi-Layer Perceptrons (MLPs) and densely connected CPGs consistently outperform deeper, more complex architectures. Contrary to trends in other AI domains, massive networks did not win across the majority of robotic locomotion tasks tested.

This penalty is particularly evident in "frugal" tasks that punish high energy usage. Large PPO-based networks struggled to learn meaningful behaviors because they attempted to optimize too many variables against a restrictive reward function. They suffered from an over-fitting penalty, failing to overcome the initial exploration phase, whereas simpler, leaner models succeeded.

## Counterarguments / Data Gaps

In many other domains of AI, such as natural language processing or computer vision, over-parameterization coupled with massive datasets generally leads to better generalization (often referred to as "scaling laws"). The robotics domain's reliance on constrained physics simulators and highly specific reward functions might uniquely disadvantage large models in this specific context.

## Related Concepts

[[Parameter Impact]] [[Multi-Layer Perceptrons (MLPs)]]

