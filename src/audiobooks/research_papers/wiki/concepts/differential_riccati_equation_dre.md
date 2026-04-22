---
title: Differential Riccati Equation (DRE)
type: concept
sources:
- Learning the Riccati solution operator for time-varying LQR via Deep Operator Networks
  (2026)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Control Theory
- Optimal Control
- Mathematical Optimization
---

## TLDR

The DRE is a nonlinear matrix-valued differential equation central to finding optimal feedback laws in Linear Quadratic Regulator (LQR) control systems.

## Body

The Differential Riccati Equation (DRE) is the mathematical cornerstone of LQR control, defining the evolution of the optimal cost-to-go matrix over time. In optimal control, minimizing a quadratic cost function subject to linear dynamics requires solving this equation to determine the optimal feedback gain. 

When systems are time-varying, the coefficients of the DRE change, necessitating a re-computation of the Riccati solution. This process is inherently iterative and non-linear, making it the primary computational bottleneck in high-frequency control loops like Model Predictive Control (MPC).

## Counterarguments / Data Gaps

While the DRE provides an optimal solution, it assumes perfect model knowledge and linear system dynamics. In many real-world scenarios, the assumption of linearity is overly simplistic, and the computational complexity often leads practitioners to use approximate, suboptimal methods instead of solving the DRE exactly.

## Related Concepts

[[Linear Quadratic Regulator (LQR)]] [[Model Predictive Control (MPC)]] [[Differential Games]]

