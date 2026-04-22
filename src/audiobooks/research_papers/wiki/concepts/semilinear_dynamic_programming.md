---
title: Semilinear Dynamic Programming
type: concept
sources:
- 'Li, Yuchao and Bertsekas, Dimitri, ''Semilinear Dynamic Programming: Analysis,
  Algorithms, and Certainty Equivalence Properties'''
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimal Control
- Stochastic Optimization
- Dynamic Programming
---

## TLDR

A mathematical framework that extends the analytical elegance of Linear-Quadratic control to more complex systems while maintaining tractability.

## Body

Semilinear Dynamic Programming represents a structural approach to solving stochastic optimization problems by expanding upon the properties of classical Linear-Quadratic (LQ) control. While traditional LQ control relies on linear dynamics and quadratic costs to yield closed-form solutions, Semilinear Dynamic Programming relaxes these strict requirements to capture a broader range of real-world behaviors without abandoning the solvability inherent in simple models.

The framework provides a systematic way to decompose complex optimization problems into manageable components. By identifying specific structures that mimic the 'certainty equivalence' properties found in LQ control, the authors enable practitioners to derive optimal policies that avoid the exponential computational costs typically associated with solving the Bellman equation via brute-force methods.

## Counterarguments / Data Gaps

The primary limitation is that 'semilinearity' is a restrictive structural assumption; problems that do not adhere to these specific algebraic forms cannot leverage the method. Additionally, the approach may struggle in highly nonlinear or stochastic environments where the simplifying assumptions of certainty equivalence break down under extreme uncertainty.

## Related Concepts

[[Linear-Quadratic Control]] [[Bellman Equation]] [[Certainty Equivalence]] [[Agent-Based Modeling]]

