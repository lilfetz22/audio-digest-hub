---
title: Two-Phase Sequencing and Trajectory Planning
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Operations Research
- Air Traffic Management
- Optimization
---

## TLDR

A hybrid optimization architecture that first determines aircraft landing order using Mixed-Integer Linear Programming and then optimizes flight paths using Nonlinear Programming.

## Body

This architecture decouples the combinatorial problem of aircraft sequencing from the continuous problem of trajectory generation. Phase 1, the Sequencer, utilizes a Mixed-Integer Linear Program (MILP) to identify the optimal landing order, incorporating 'Constrained Position Shifting' (CPS) to manage wake-turbulence separation constraints while limiting total position changes.

Once the order is determined, Phase 2 (the Trajectory Planner) utilizes a Nonlinear Program (NLP) to fine-tune the flight path. This phase focuses on optimizing speed profiles and precise path-stretching based on the locked sequence, ensuring that the physical constraints of flight dynamics are satisfied in a computationally efficient manner.

## Counterarguments / Data Gaps

The two-phase approach can be suboptimal because the sequencing phase might make decisions that limit the feasibility or efficiency of the trajectory planning phase. By solving these as separate steps rather than a single integrated optimization, the system may miss global optima that require tradeoffs between sequencing and path length.

## Related Concepts

[[Mixed-Integer Linear Programming]] [[Nonlinear Programming]] [[Constrained Position Shifting]]

