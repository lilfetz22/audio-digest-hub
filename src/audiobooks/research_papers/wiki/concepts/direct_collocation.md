---
title: Direct Collocation
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Numerical Optimization
- Optimal Control
---

## TLDR

A numerical method for solving optimal control problems by discretizing states and controls over time and imposing dynamics as equality constraints.

## Body

Direct collocation discretizes the state and control variables over a time grid. Instead of solving the differential equations forward in time from an initial guess, the algorithm treats the values at each point as independent variables in a constrained optimization problem.

The dynamics of the system are enforced as algebraic equality constraints between adjacent points in the trajectory. This approach is highly favored in trajectory optimization because it is generally more robust than shooting methods, as it avoids the sensitivity issues inherent in integrating unstable dynamic systems over long horizons.

## Counterarguments / Data Gaps

Direct collocation can lead to very large optimization problems, requiring significant memory and powerful solvers. Furthermore, the accuracy of the solution is strictly tied to the discretization grid; if the grid density does not capture the system's underlying dynamic curvature, the solution may be physically inconsistent.

## Related Concepts

[[Shooting Methods]] [[Nonlinear Programming]]

