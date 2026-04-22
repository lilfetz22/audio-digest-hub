---
title: Nadir-CHIM Method
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimization
- Control Theory
- Multi-objective Optimization
---

## TLDR

A multi-objective optimization strategy that leverages objective space geometry to handle non-convex or pathological Pareto fronts.

## Body

The Nadir-CHIM (Convex Hull of Individual Minima) method is designed to overcome the limitations of traditional weighted-sum approaches in multi-objective control problems. By focusing on the 'nadir' point and the convex hull of individual optima, the method avoids the instability and 'chattering' effects common when optimizing across warped or non-convex Pareto surfaces.

Unlike static weighting, which often fails to find solutions in non-convex regions, Nadir-CHIM uses the geometry of the objective space to inform the optimization path. This allows the controller to maintain stability while navigating trade-offs between conflicting objectives, ensuring consistent performance in complex environments.

## Counterarguments / Data Gaps

The method relies on accurately identifying the individual minima of the objective space; if these are computationally expensive to calculate, the overhead may negate the benefits of the geometric approach. Additionally, performance may degrade if the Pareto front is highly dynamic or shifts rapidly in ways the convex hull estimation cannot track.

## Related Concepts

[[Pareto Front]] [[Weighted-Sum Method]] [[Convex Optimization]]

