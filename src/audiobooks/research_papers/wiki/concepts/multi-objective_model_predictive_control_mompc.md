---
title: Multi-Objective Model Predictive Control (MOMPC)
type: concept
sources:
- "Individual Minima-Informed Multi-Objective Model Predictive Control for Fixed Point\
  \ Stabilization, Markus Herrmann-Wicklmayr and Kathrin Fla\xDFkamp"
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Control Theory
- Optimization
- Automation
---

## TLDR

A control strategy that optimizes for multiple conflicting objectives simultaneously by navigating the Pareto front to determine an optimal trade-off point.

## Body

Multi-Objective Model Predictive Control extends standard MPC by managing systems where a single cost function is insufficient to capture competing requirements. In many real-world applications, such as HVAC climate control or autonomous vehicle navigation, system objectives (e.g., energy efficiency vs. performance) inherently conflict.

Traditional MPC struggles with these scenarios because it often requires scalarization or heavy computational effort to resolve the Pareto front in real-time. By utilizing a multi-objective approach, the controller maintains a set of trade-off solutions, allowing the system to balance performance indices dynamically based on the current state.

## Counterarguments / Data Gaps

The primary limitation of MOMPC is the computational overhead associated with calculating or approximating the Pareto front, which can lead to control latency. Furthermore, defining the weights for different objectives often requires domain expertise, as the mathematical formulation may not always align with subjective human preferences for 'comfort' or 'safety'.

## Related Concepts

[[Model Predictive Control]] [[Pareto Optimization]] [[Optimal Control]]

