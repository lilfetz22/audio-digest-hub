---
title: Semi-DCNLP (Semi-Direct Collocation with Nonlinear Programming)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimal Control
- Differential Games
- Numerical Optimization
---

## TLDR

A method for solving differential games by discretizing trajectories and embedding the follower's optimality conditions as algebraic constraints within the leader's optimization problem.

## Body

Semi-DCNLP transforms complex differential games into a singular constrained nonlinear programming (NLP) problem. Rather than solving differential equations through integration or analytical derivation, the method discretizes the state and control variables across a trajectory. This conversion turns a dynamic game into a static mathematical programming problem where the variables at each collocation point are treated as decision parameters.

The 'Semi' designation refers to the strategic integration of the follower's optimality conditions directly into the leader's constraint set. Specifically, the follower's costate equations are mapped as hard algebraic boundaries, forcing the leader to optimize their strategy while strictly adhering to the follower's optimal response surface. This architecture allows the system to treat the leader-follower hierarchy as a single, cohesive optimization landscape rather than a nested iterative loop.

By framing the game in this way, the method leverages mature, robust numerical solvers like SNOPT. This eliminates the need for the manual, often error-prone derivation of complex analytical gradients, allowing for the discovery of global optima in high-dimensional or non-intuitive state spaces.

## Counterarguments / Data Gaps

While the approach simplifies the derivation process, it relies heavily on the quality and convergence properties of the underlying NLP solver. Large-scale discretization can lead to high-dimensional optimization problems that may become computationally expensive or fall into local minima depending on the initial guess.

Additionally, the method assumes the follower's optimality conditions are well-defined and can be expressed as algebraic constraints. This may be difficult to implement in scenarios where the follower's objective function is non-smooth, non-convex, or involves discontinuities that are not easily captured by standard costate equations.

## Related Concepts

[[Direct Collocation]] [[Nonlinear Programming (NLP)]] [[Shooting Methods]] [[Stackelberg Games]]

