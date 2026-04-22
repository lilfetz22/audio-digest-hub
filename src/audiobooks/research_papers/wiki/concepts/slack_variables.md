---
title: Slack Variables
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Optimization
- Constrained Optimization
---

## TLDR

A technique used to map constrained control spaces into unconstrained spaces by introducing additional variables to represent the deviation from constraint boundaries.

## Body

Slack variables allow an optimization algorithm to treat constrained control spaces as if they were unconstrained. By introducing a variable that accounts for the difference between a state and its constraint boundary, the solver can operate in a 'slackened' space, effectively smoothing the optimization landscape.

This provides the solver with more freedom to explore the feature space without getting trapped at hard boundary conditions. It transforms inequality constraints into equality constraints, which is often easier for numerical optimization solvers to handle during the iteration process.

## Counterarguments / Data Gaps

The addition of slack variables increases the total dimensionality of the problem, which can lead to longer convergence times per iteration. Furthermore, if not properly regularized, the solver might exploit the slack variables to avoid satisfying the underlying physical constraints of the system.

## Related Concepts

[[Lagrange multipliers]] [[Feature space exploration]]

