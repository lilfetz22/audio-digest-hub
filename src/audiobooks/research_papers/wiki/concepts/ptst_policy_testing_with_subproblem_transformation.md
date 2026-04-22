---
title: PTST (Policy Testing with Subproblem Transformation)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Reinforcement Learning
- Algorithms
- Policy Optimization
---

## TLDR

An algorithm that achieves instance-optimal performance by decomposing high-dimensional policy testing constraints into independent, solvable sub-grids.

## Body

PTST operates by partitioning the complex global constraints of policy testing into a grid of 'product-box' subproblems. Each subproblem represents a local constraint space that can be addressed independently, avoiding the pitfalls of generic, loose convex relaxations that typically result in suboptimal performance.

By utilizing projected policy gradient methods on these sub-grids, PTST adapts its sample complexity to the inherent difficulty of the specific MDP instance. This makes it 'asymptotically instance-optimal,' meaning it performs efficiently relative to the difficulty of the individual task at hand rather than relying on worst-case bounds.

## Counterarguments / Data Gaps

The effectiveness of the grid decomposition depends heavily on the granularity of the sub-grids; if the grid is too coarse, it may fail to capture the nuances of the policy space, while an overly fine grid leads to high computational overhead. Additionally, the reliance on projected gradient methods assumes that the projection step onto the product-box is computationally inexpensive.

## Related Concepts

[[Policy Gradient Methods]] [[Instance Optimality]]

