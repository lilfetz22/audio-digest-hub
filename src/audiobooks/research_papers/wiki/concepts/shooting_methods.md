---
title: Shooting Methods
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Numerical Analysis
- Optimal Control
---

## TLDR

A traditional numerical technique for solving boundary value problems in optimal control by converting them into initial value problems, often characterized by high accuracy but poor convergence.

## Body

Shooting methods are a classic approach to solving differential equations in optimal control. The core idea is to guess the initial conditions (the 'shooting' parameters) and integrate the system forward in time until a terminal state is reached. The algorithm then adjusts the initial guess based on the error between the result and the target boundary conditions.

In the context of differential games, shooting methods are considered the gold standard for high-fidelity accuracy. They provide precise results because they treat the system as a continuous dynamic evolution. However, they are notoriously sensitive to the initial guess, making them difficult to converge in complex or unstable state spaces.

## Counterarguments / Data Gaps

The primary limitation of shooting methods is their numerical instability; for complex systems or long time horizons, small errors in the initial 'shot' can lead to divergent trajectories. This sensitivity makes them difficult to automate without a very strong initial estimate.

## Related Concepts

[[Boundary Value Problems]] [[Initial Value Problems]]

