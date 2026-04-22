---
title: Piecewise-Stationary MDPs
type: concept
sources:
- 'DARLING: Detection Augmented Reinforcement Learning with Non-Stationary Guarantees'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Reinforcement Learning
- Stochastic Modeling
---

## TLDR

A modeling framework for environments where reward and transition dynamics remain constant over intervals before experiencing abrupt, discrete changes.

## Body

Piecewise-Stationary (PS) Markov Decision Processes (MDPs) are used to represent environments that are not strictly stationary but do not change continuously either. In this framework, the underlying physics or logic of the system remains stable for finite durations (epochs) before shifting to a new configuration.

This abstraction allows researchers to apply reinforcement learning techniques to real-world scenarios, such as finance or supply chain management, where structural shifts occur due to external events. By modeling change as discrete jumps rather than continuous drift, the PS-MDP framework enables the development of algorithms that reset or adjust their policy when a change is detected.

## Counterarguments / Data Gaps

The primary limitation is that many real-world environments do not exhibit sudden, discrete changes but rather evolve through slow, continuous non-stationarity. Using a PS-MDP model in such contexts can lead to significant modeling errors, as the agent may fail to adapt to gradual trends that do not trigger a 'jump' detection.

## Related Concepts

[[Non-Stationary Reinforcement Learning]] [[Markov Decision Processes]]

