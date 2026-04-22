---
title: Semi-DCNLP
type: concept
sources:
- A Numerical Analysis for Pursuit-Evasion Games under the Stackelberg Equilibrium
  by Kazuhiro Horie
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Numerical Analysis
- Control Theory
- Computational Mathematics
---

## TLDR

A numerical method designed to solve the complex differential equations inherent in pursuit-evasion games by leveraging the hierarchical structure of Stackelberg equilibria.

## Body

Semi-DCNLP (Semi-Direct Collocation Nonlinear Programming) is a numerical technique employed to address the sensitivities associated with solving two-point boundary-value problems (TPBVPs) in control theory. Traditional methods for solving these games often suffer from extreme instability, where minor errors in initial guesses lead to divergent numerical simulations.

By utilizing direct collocation, the method discretizes the continuous state and control trajectories into a finite set of points, effectively transforming the differential game into a nonlinear programming (NLP) problem. This semi-discretized approach allows the solver to handle the hierarchy imposed by the Stackelberg equilibrium more robustly than shooting methods, as it optimizes over the entire trajectory simultaneously rather than integrating from a single point.

## Counterarguments / Data Gaps

Direct collocation methods can result in very large-scale NLP problems, requiring high-performance solvers and substantial memory allocation. The accuracy of the solution is also strictly bounded by the density of the collocation points, meaning that poor discretization can lead to significant discretization error that might not be immediately apparent without refined sensitivity analysis.

## Related Concepts

[[Direct Collocation]] [[Nonlinear Programming]] [[Two-Point Boundary-Value Problem]]

