---
title: Linear Quadratic Gaussian (LQG) Control
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

An extension of LQR that accounts for partial observability and stochastic noise, reflecting realistic sensor inputs in autonomous systems.

## Body

Linear Quadratic Gaussian (LQG) control addresses the disconnect between idealized control models and reality by incorporating stochastic noise and partial observability. Unlike LQR, LQG acknowledges that the agent cannot know the true state of the environment, receiving only noisy, incomplete sensor data as input. This necessitates the use of an estimator—typically a Kalman filter—to maintain a probabilistic belief about the system state.

By coupling an optimal estimator with an optimal regulator (Separation Principle), LQG provides a robust framework for controlling agents in uncertain conditions. It is essential for modern robotics and autonomous systems where sensor uncertainty is an inherent constraint rather than an edge case.

## Counterarguments / Data Gaps

While theoretically robust, LQG models can be computationally expensive to implement in high-dimensional state spaces. Additionally, if the noise characteristics of the environment deviate from the Gaussian assumptions modeled in the controller, performance can degrade significantly.

## Related Concepts

[[LQR]] [[Kalman Filtering]] [[Partial Observability]] [[Stochastic Control]]

