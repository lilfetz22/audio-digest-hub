---
title: Pascoletti-Serafini (PS) Scalarization
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimization
- Multi-Objective Optimization
- Mathematical Programming
---

## TLDR

A multi-objective optimization technique that scalarizes a vector-valued problem by shooting a ray from a chosen point toward the Pareto front.

## Body

The Pascoletti-Serafini (PS) scalarization is a sophisticated approach to multi-objective optimization that moves beyond simple weighted-sum methods. It functions by defining a 'shooting direction' and a 'shooting origin,' effectively projecting a ray from a point in the objective space toward the Pareto front. By finding the intersection point, it identifies a solution that satisfies specific preference requirements.

This method is particularly useful because it avoids the pitfalls of convex weighted sums, which struggle to find solutions in non-convex regions of the Pareto front. By using the convex hull of individual minima as the starting point, the PS scalarization ensures that the optimization process is grounded in the extreme capabilities of the system, allowing for a more controlled search of optimal trade-offs.

## Counterarguments / Data Gaps

The primary limitation of PS scalarization is its reliance on the selection of appropriate shooting directions and origins; an poorly chosen origin can lead to inefficient exploration of the Pareto front. Furthermore, the mathematical complexity of calculating the intersection points can be computationally expensive compared to simpler heuristic methods.

## Related Concepts

[[Pareto Front]] [[Convex Hull]] [[Scalarization]]

