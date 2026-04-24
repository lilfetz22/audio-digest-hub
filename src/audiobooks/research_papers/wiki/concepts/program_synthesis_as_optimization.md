---
title: Program Synthesis as Optimization
type: concept
sources:
- 'EvolveSignal: A Large Language Model Powered Coding Agent for Discovering Traffic
  Signal Control Strategies'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.9
categories:
- Optimization
- Software Engineering
- Machine Learning Methodology
---

## TLDR

An approach where complex optimization problems are solved by having an AI write explicit, executable code rather than training a black-box predictive model.

## Body

Traditionally, complex optimization tasks have been handled by training black-box models, such as deep neural networks or reinforcement learning agents, to map inputs directly to outputs. Program synthesis flips this paradigm by framing the optimization task as a code-generation problem.

In the context of traffic control, this methodology treats the traffic signal logic as a Python function. An LLM synthesizes a program that takes specific intersection features—such as lane layouts and traffic volume—as inputs, and outputs an optimized signal timing plan. This results in explicit, readable heuristics rather than opaque model weights.

## Counterarguments / Data Gaps

While synthesized programs are highly interpretable and easy to deploy on traditional hardware, their effectiveness is heavily bottlenecked by the LLM's coding capabilities and the quality of the prompt. Additionally, a static synthesized program cannot continuously learn and adapt in real-time to sudden environmental changes the way a live Reinforcement Learning model can.

## Related Concepts

[[Program Synthesis]] [[Black-Box Models]] [[EvolveSignal]]

