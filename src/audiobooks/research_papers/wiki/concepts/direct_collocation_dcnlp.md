---
title: Direct Collocation (DCNLP)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Trajectory Planning
- Numerical Optimization
- Control Theory
---

## TLDR

A trajectory optimization method that treats the trajectory as a set of algebraic constraints, offering superior numerical stability over traditional shooting methods.

## Body

Direct Collocation (DCNLP) shifts the focus from 'shooting'—where an initial guess is iteratively adjusted—to a discretization approach. By converting the continuous trajectory problem into a set of algebraic constraints at specific nodes, the optimizer can handle the path as a holistic structure rather than an initial value problem.

This method is generally more forgiving regarding the initial guess and exhibits greater numerical stability. By framing trajectory planning as an algebraic constraint problem, practitioners avoid the divergence issues commonly associated with the sensitivity of long-horizon shooting methods.

## Counterarguments / Data Gaps

Direct collocation significantly increases the number of decision variables in the optimization problem because every discretization point must be accounted for by the solver. This leads to high-dimensional sparse matrices that require specialized, computationally expensive solvers compared to simple shooting methods.

## Related Concepts

[[Shooting methods]] [[Trajectory optimization]] [[DCNLP]]

