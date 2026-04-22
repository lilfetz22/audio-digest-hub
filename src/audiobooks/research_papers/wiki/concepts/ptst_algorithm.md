---
title: PTST Algorithm
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Reinforcement Learning
- Algorithm Design
- Sample Complexity
---

## TLDR

A policy testing algorithm that achieves instance-optimality by decomposing constraints into independent grid-based subproblems.

## Body

The PTST (Policy Testing Subproblem Transformation) algorithm is designed to address the challenges of policy verification in high-dimensional state spaces. It works by breaking down the global constraint problem into a 'product-box' grid, where each segment of the grid is solved independently.

By utilizing projected policy gradient methods on these sub-grids, PTST avoids the pitfalls of generic convex relaxations, which are often too loose for practical application. This granular approach ensures that the sample complexity is tied directly to the difficulty of the specific MDP instance being tested, rather than a worst-case theoretical bound.

## Counterarguments / Data Gaps

The primary limitation of grid-based decomposition is the 'curse of dimensionality,' where the number of subproblems grows exponentially with the state space size. This may necessitate heuristic approximations for large-scale systems, potentially undermining the instance-optimality guarantees.

## Related Concepts

[[Reversed MDP]] [[Projected Policy Gradient]] [[Instance-Optimality]]

