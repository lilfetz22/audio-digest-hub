---
title: Hamilton-Jacobi-Bellman (HJB) Equation
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimal Control
- Stochastic Processes
- Mathematics
---

## TLDR

A partial differential equation central to optimal control theory that characterizes the value function of a dynamic optimization problem.

## Body

The HJB equation serves as the mathematical foundation for finding the optimal control policy that minimizes a cost functional over time. In its standard form, it is typically non-linear and computationally intensive to solve directly.

By incorporating a quadratic penalty on the control effort (the drift of the SDE), the equation becomes amenable to the Cole-Hopf transformation. This transformation maps the non-linear HJB equation into a linear heat equation, effectively changing the difficulty of the optimization problem from solving a complex PDE to solving a linear diffusion process.

## Counterarguments / Data Gaps

The primary limitation of HJB-based approaches is the 'curse of dimensionality,' where the computational cost grows exponentially with the state space dimension. Furthermore, the reliance on the Cole-Hopf transformation requires specific problem structures (often involving quadratic costs) that may not generalize to all practical machine learning loss functions.

## Related Concepts

[[Cole-Hopf Transformation]] [[Stochastic Differential Equations]] [[Value Function]]

