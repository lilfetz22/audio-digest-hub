---
title: Model Granularity Sensitivity
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.88
categories:
- Modeling
- Systems Engineering
- Optimization
---

## TLDR

The principle that not all modeling variables contribute equally to system efficiency, with geometric path variables often outperforming speed variables in sensitivity.

## Body

When developing optimization models for physical systems like air traffic, data scientists must decide where to allocate computational precision. This research indicates that the discretization of path-stretch distances is a more critical lever for performance than speed discretization.

Focusing precision on variables that have a direct, high-impact effect on the objective function allows for more efficient models. By simplifying lower-impact variables (like minor speed adjustments), developers can maintain model accuracy while significantly reducing the computational load required for real-time decision support.

## Counterarguments / Data Gaps

Over-simplifying speed discretization can lead to unrealistic flight profiles if the model ignores the kinetic constraints of the aircraft. There is a risk that by focusing exclusively on path-stretch geometry, the model may generate sequences that are physically infeasible or unsustainable for real-world pilots.

## Related Concepts

[[Discretization]] [[Objective Function Optimization]] [[Agent-based Systems]]

