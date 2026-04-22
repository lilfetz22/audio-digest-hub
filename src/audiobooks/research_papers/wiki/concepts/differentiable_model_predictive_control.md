---
title: Differentiable Model Predictive Control
type: concept
sources:
- '2026 Conference on Learning for Dynamics and Control: ''Policy Optimization for
  Unknown Systems using Differentiable Model Predictive Control'''
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Control Theory
- Reinforcement Learning
- Robotics
---

## TLDR

An approach to control that embeds predictive models directly into a differentiable pipeline to handle uncertainty in system dynamics.

## Body

Differentiable Model Predictive Control (DMPC) attempts to solve the 'model-based dilemma' where system models are often inaccurate approximations. By making the MPC process differentiable, researchers can refine the system model parameters or the control policy directly through gradient-based optimization. This allows the agent to adjust its internal dynamics model based on the success or failure of its control actions.

In this framework, the control system is not just an execution engine but a dynamic part of the learning loop. When the system model is imperfect, DMPC allows for the propagation of errors back through the controller, forcing the policy to become more robust to model inaccuracies and improving stability in complex control environments.

## Counterarguments / Data Gaps

The primary challenge with DMPC is the 'sim-to-real' gap and the instability introduced when gradients are computed from inaccurate models. If the base model deviates too significantly from physical reality, the gradients may point toward suboptimal or unsafe control strategies, leading to divergence in training.

## Related Concepts

[[Model Predictive Control]] [[System Identification]] [[Policy Optimization]]

