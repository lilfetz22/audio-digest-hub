---
title: Linear Quadratic Regulator (LQR)
type: concept
sources:
- 'Multitask LQG Control: Performance and Generalization Bounds (April 2026)'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Control Theory
- Robotics
- Optimal Control
---

## TLDR

A classical optimal control framework that provides optimal policy convergence for linear systems under the assumption of perfect, noise-free state observability.

## Body

The Linear Quadratic Regulator (LQR) is a fundamental control theoretic approach for systems governed by linear dynamics with a quadratic cost function. It operates under the assumption that the controller has access to the full, noise-free state of the environment. Because of this complete information, LQR allows for the derivation of optimal control laws that minimize cost over time while guaranteeing convergence to a stable policy.

In the context of autonomous systems, LQR is considered the gold standard for its mathematical elegance and reliability. By simplifying the problem to a deterministic state, it provides a baseline for evaluating more complex control architectures, serving as the benchmark against which modern adaptive control strategies are often measured.

[NEW RESEARCH ADDITION]: LQR provides a framework for steering a dynamical system to a target state while minimizing a quadratic cost function, assuming that the system dynamics are linear and the state of the system is fully known at all times. Because it assumes perfect information, LQR allows for strong mathematical guarantees regarding policy optimality. It serves as a foundational benchmark for control tasks where environmental uncertainty and sensory noise are minimal or can be effectively abstracted away.

## Counterarguments / Data Gaps

The primary limitation of LQR is its reliance on the assumption of perfect state information. In real-world physical environments, noise, sensor latency, and occlusions make this assumption unrealistic, rendering LQR policies brittle or ineffective in practical deployments. [NEW RESEARCH ADDITION]: In most real-world physical environments, noise is inherent, making the assumption of a noise-free state unrealistic and often leading to performance failures in practical robotic applications.

## Related Concepts

[[Linear Quadratic Gaussian (LQG)]] [[Optimal Control]]

