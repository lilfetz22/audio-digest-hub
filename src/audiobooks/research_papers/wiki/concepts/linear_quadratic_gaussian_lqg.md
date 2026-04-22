---
title: Linear Quadratic Gaussian (LQG)
type: concept
sources:
- 'Multitask LQG Control: Performance and Generalization Bounds (April 2026)'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Control Theory
- Stochastic Systems
- Robotics
---

## TLDR

An extension of LQR that addresses real-world control challenges by incorporating partial observability and stochastic noise.

## Body

LQG control is designed for systems where the state is not directly observable and is instead inferred through noisy sensor outputs. Unlike LQR, LQG explicitly accounts for the stochastic nature of both the process noise (disturbances in dynamics) and the measurement noise (sensor inaccuracies).

By integrating state estimation—typically through a Kalman filter—with a control law, LQG allows agents to operate in environments that are not perfectly known. This makes it significantly more robust for real-world autonomous systems and robotics compared to the idealized LQR model.

## Counterarguments / Data Gaps

While more realistic than LQR, LQG systems are mathematically more complex and computationally demanding. They are also subject to the 'Separation Principle,' which assumes the estimator and controller can be designed independently, a condition that may not always hold in highly nonlinear or non-Gaussian real-world settings.

## Related Concepts

[[Linear Quadratic Regulator (LQR)]] [[State Estimation]] [[Kalman Filter]]

