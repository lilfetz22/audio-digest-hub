---
title: Reflector Pattern
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Agentic AI
- Optimization
- System Architecture
---

## TLDR

An agentic design strategy that treats optimization as an iterative loop where results are validated against domain-specific simulations to escape local optima.

## Body

The Reflector pattern shifts the focus from achieving immediate accuracy to an iterative refinement process. Instead of expecting a large language model to output the perfect solution in a single pass, the system utilizes a feedback loop where the agent's proposed actions are tested within a controlled environment or simulation.

By treating the domain-specific simulation as a 'ground truth' oracle, the agent can analyze the performance outcomes of its previous decisions. This allows the agent to identify when it has become trapped in a local optimum and apply self-correction strategies to adjust its parameters, significantly improving performance in high-dimensional or complex optimization tasks.

## Counterarguments / Data Gaps

The primary limitation of the Reflector pattern is the high latency introduced by iterative simulation cycles, which may make it unsuitable for real-time applications requiring millisecond responses. Additionally, the effectiveness of the pattern is entirely dependent on the fidelity and speed of the underlying simulation environment.

## Related Concepts

[[Iterative Optimization]] [[Simulation-in-the-loop]] [[Self-Correction]]

