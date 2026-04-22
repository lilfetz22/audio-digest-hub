---
title: Conservative Jacobian
type: concept
sources:
- Zuliani et al.
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Control Theory
- Optimization
---

## TLDR

A sensitivity measure derived from an imperfect model that maps parameter changes to decision outcomes while accounting for model uncertainty.

## Body

The conservative Jacobian is a specialized gradient computation designed for Model Predictive Control (MPC). Unlike standard gradients that assume a perfect model, this method acknowledges that the internal model is an approximation. It serves as a directional guide for optimization, indicating how parameter adjustments are expected to affect the MPC’s output.

By treating the internal model as a non-definitive map, the conservative Jacobian allows the optimization process to move efficiently through the parameter space. It filters out high-frequency noise that might be present in a naive gradient estimate, providing a smoother trajectory toward the cost minimum.

## Counterarguments / Data Gaps

Deriving a robust Jacobian often requires making restrictive assumptions about the structure of the model's errors. If the internal model is fundamentally misaligned with the environment's dynamics, even a 'conservative' approach will propagate systemic bias into the optimization process, potentially leading the policy toward a local minimum that does not exist in the real world.

## Related Concepts

[[Jacobian Matrix]] [[Sensitivity Analysis]] [[Model Predictive Control (MPC)]]

