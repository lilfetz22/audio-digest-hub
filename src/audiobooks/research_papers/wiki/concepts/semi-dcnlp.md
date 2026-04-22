---
title: Semi-DCNLP
type: concept
sources:
- Horie, K. (2026). A Numerical Analysis for Pursuit-Evasion Games under the Stackelberg
  Equilibrium.
- A Numerical Analysis for Pursuit-Evasion Games under the Stackelberg Equilibrium
  by Kazuhiro Horie
- Horie, K. (2026). Semi-Direct Collocation and Nonlinear Programming for Bilevel
  Differential Games.
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Numerical Analysis
- Control Theory
- Computational Mathematics
---

## TLDR

A trajectory optimization method that solves Stackelberg pursuit-evasion games by converting differential equations into large-scale nonlinear programming problems where the follower's optimality conditions are embedded as algebraic constraints.

## Body

Semi-DCNLP (Semi-Direct Collocation Nonlinear Programming) is a numerical technique employed to address the sensitivities associated with solving two-point boundary-value problems (TPBVPs) in control theory. Traditional methods for solving these games often suffer from extreme instability, where minor errors in initial guesses lead to divergent numerical simulations.

By utilizing direct collocation, the method discretizes the continuous state and control trajectories into a finite set of points, effectively transforming the differential game into a nonlinear programming (NLP) problem. This semi-discretized approach allows the solver to handle the hierarchy imposed by the Stackelberg equilibrium more robustly than shooting methods, as it optimizes over the entire trajectory simultaneously rather than integrating from a single point.

[Existing Findings]: Semi-DCNLP acts as a bridge between the theoretical definition of the game and the numerical reality of trajectory generation. By discretizing the state and control trajectories over time, it converts the differential equations into a set of algebraic constraints, enabling the application of robust numerical solvers to complex bilevel optimization problems.

[New Findings]: Semi-DCNLP stands for Semi-Direct Collocation with Nonlinear Programming. Unlike traditional analytical approaches that solve differential equations directly, this method discretizes a trajectory into a series of points. These points, representing state and control variables, are treated as parameters within a large-scale optimization framework. The 'Semi' component refers to the integration of the follower’s optimality conditions—specifically their costate equations—directly into the leader’s optimization problem. By embedding the follower’s 'best response' logic into the leader’s constraints, the method effectively forces the follower's optimal behavior to serve as a boundary condition for the leader's decision space. This transformation allows researchers to leverage high-performance numerical solvers, such as SNOPT, to identify optima, bypassing the need for manual derivation of complex analytical gradients.

## Counterarguments / Data Gaps

Direct collocation methods can result in very large-scale NLP problems, requiring high-performance solvers and substantial memory allocation. The accuracy of the solution is also strictly bounded by the density of the collocation points, meaning that poor discretization can lead to significant discretization error that might not be immediately apparent without refined sensitivity analysis. Additionally, the method is highly dependent on the quality of the initial guess, and the computational cost increases significantly as the discretization density grows, making it difficult to achieve high-fidelity solutions in real-time scenarios. Furthermore, the method relies on the follower being perfectly rational and following the assumed optimality conditions, which may not hold in real-world environments with noise or adversarial agents; additionally, coarse discretization can miss high-frequency dynamics.

## Related Concepts

[[Direct Collocation]] [[Nonlinear Programming]] [[Differential Games]] [[Costate Equations]]

