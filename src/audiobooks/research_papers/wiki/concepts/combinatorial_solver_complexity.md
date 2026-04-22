---
title: Combinatorial Solver Complexity
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Optimization
- Computational Complexity
- Scheduling
---

## TLDR

The phenomenon where scheduling algorithms experience exponential runtime growth as the number of allowed position shifts increases.

## Body

In agent-based scheduling, allowing agents to shift positions to optimize for a specific metric (like fuel or time) creates a combinatorial search space. As the number of possible shifts increases, the search tree for algorithms like branch-and-bound grows significantly, leading to unpredictable latency in high-traffic scenarios.

The study suggests that capping the search depth—limiting how many positions an aircraft can 'jump'—is an effective strategy for maintaining real-time feasibility. This heuristic prevents the solver from getting stuck in deep search trees caused by symmetric constraints, where multiple agents are effectively tied for priority.

## Counterarguments / Data Gaps

Capping the shift range introduces a fundamental trade-off: it ensures real-time performance at the cost of global optimality. By restricting the solver, the system may miss a theoretically superior global sequencing solution that would have been found with a deeper search.

## Related Concepts

[[Branch-and-Bound]] [[Combinatorial Explosion]] [[CPS Resequencing]]

