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

A classical optimal control framework that assumes full state observability and deterministic system dynamics to achieve guaranteed convergence.

## Body

The Linear Quadratic Regulator (LQR) is a fundamental control theoretic approach for systems governed by linear dynamics with a quadratic cost function. It operates under the assumption that the controller has access to the full, noise-free state of the environment. Because of this complete information, LQR allows for the derivation of optimal control laws that minimize cost over time while guaranteeing convergence to a stable policy.

In the context of autonomous systems, LQR is considered the gold standard for its mathematical elegance and reliability. By simplifying the problem to a deterministic state, it provides a baseline for evaluating more complex control architectures, serving as the benchmark against which modern adaptive control strategies are often measured.

## Counterarguments / Data Gaps

The primary limitation of LQR is its reliance on the assumption of perfect state information. In real-world physical environments, noise, sensor latency, and occlusions make this assumption unrealistic, rendering LQR policies brittle or ineffective in practical deployments.

## Related Concepts

[[Linear Quadratic Gaussian (LQG)]] [[Stochastic Optimal Control]] [[State Estimation]]

