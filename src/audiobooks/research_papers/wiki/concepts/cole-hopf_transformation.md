---
title: Cole-Hopf Transformation
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Mathematical Optimization
- Control Theory
- Stochastic Calculus
---

## TLDR

A mathematical technique that converts non-linear Hamilton-Jacobi-Bellman (HJB) equations into linear heat equations.

## Body

The Cole-Hopf transformation is a critical analytical bridge in control theory and partial differential equations (PDEs). By mapping a non-linear PDE, specifically the HJB equation governing optimal control, to a linear heat equation, it renders complex optimization problems solvable through standard linear operator methods.

In the context of stochastic control, this transformation allows researchers to handle the non-linearity of the value function induced by the control cost. Once linearized, the problem becomes amenable to solutions using the superposition principle, simplifying the derivation of the optimal control policy.

## Counterarguments / Data Gaps

The transformation is highly specific to certain forms of PDEs, particularly those involving quadratic costs. It does not generalize easily to more complex, high-dimensional non-linearities or constraints that deviate from standard diffusive behaviors.

## Related Concepts

[[Hamilton-Jacobi-Bellman Equation]] [[Heat Equation]]

