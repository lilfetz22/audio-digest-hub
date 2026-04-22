---
title: Differentiable Model Predictive Control
type: concept
sources:
- '2026 Conference on Learning for Dynamics and Control: ''Policy Optimization for
  Unknown Systems using Differentiable Model Predictive Control'''
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Control Theory
- Reinforcement Learning
- Robotics
---

## TLDR

A control strategy that integrates differentiable optimization into MPC to allow for gradient-based policy optimization and adaptive learning in systems with unknown or imperfect dynamics.

## Body

Differentiable Model Predictive Control (DMPC) attempts to solve the 'model-based dilemma' where system models are often inaccurate approximations. By making the MPC process differentiable, researchers can refine the system model parameters or the control policy directly through gradient-based optimization. This allows the agent to adjust its internal dynamics model based on the success or failure of its control actions.

In this framework, the control system is not just an execution engine but a dynamic part of the learning loop. When the system model is imperfect, DMPC allows for the propagation of errors back through the controller, forcing the policy to become more robust to model inaccuracies and improving stability in complex control environments.

[NEW ADDITIONS]: Differentiable Model Predictive Control (MPC) extends traditional MPC by incorporating differentiability into the predictive planning stage. This allows systems to learn control policies by propagating gradients through the MPC optimization process, making it possible to refine models or policies based on observed performance. In the context of the 'model-based dilemma,' this approach addresses the issue of system identification. By making the MPC process differentiable, the controller can potentially adapt to discrepancies between the approximated system model and real-world dynamics, leading to more robust control in complex, non-linear environments.

## Counterarguments / Data Gaps

The primary challenge with DMPC is the 'sim-to-real' gap and the instability introduced when gradients are computed from inaccurate models. If the base model deviates too significantly from physical reality, the gradients may point toward suboptimal or unsafe control strategies, leading to divergence in training. [NEW ADDITIONS]: Furthermore, computational constraints often limit the time horizon for MPC, which can negatively affect long-term planning performance.

## Related Concepts

[[Model Predictive Control]] [[Policy Optimization]] [[System Identification]]

