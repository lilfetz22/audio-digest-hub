---
title: Certainty Equivalence in Stochastic Semilinear Systems
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Stochastic Control
- Reinforcement Learning
- Control Theory
---

## TLDR

The property where optimal control policies for stochastic semilinear problems can be derived by solving a deterministic surrogate using expected values.

## Body

Certainty Equivalence asserts that for a specific class of stochastic systems—specifically semilinear problems—the optimal feedback control law derived from a deterministic version of the model is identical to the optimal policy for the stochastic version. Instead of grappling with the complexities of the full stochastic Bellman equation, practitioners can substitute random variables with their expected values.

Mathematically, this simplifies the computational burden significantly. By projecting the Bellman operator into a space where the optimal policy is a stationary linear mapping, the system transforms into a structure where the optimal cost parameter vector can be solved iteratively using monotonic and concave operators. This provides a robust foundation for applying Value Iteration to stochastic control tasks.

## Counterarguments / Data Gaps

This result is generally limited to semilinear or linear-quadratic frameworks; it does not hold for arbitrary non-linear stochastic systems where the separation of estimation and control is not guaranteed. If the system dynamics or objective functions exhibit high degrees of non-linearity, the substitution of expectations may lead to significant sub-optimality.

## Related Concepts

[[Bellman Equation]] [[Stochastic Optimal Control]] [[Certainty Equivalent Control]]

