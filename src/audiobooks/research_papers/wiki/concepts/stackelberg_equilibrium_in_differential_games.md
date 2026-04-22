---
title: Stackelberg Equilibrium in Differential Games
type: concept
sources:
- Horie, K. (2026). A Numerical Analysis for Pursuit-Evasion Games under the Stackelberg
  Equilibrium.
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Control Theory
- Game Theory
- Differential Games
---

## TLDR

A hierarchical decision-making framework where a leader moves first and a follower responds optimally, simplifying the complexity of finding equilibrium trajectories.

## Body

In the context of pursuit-evasion games, the Stackelberg equilibrium models a sequential interaction rather than a simultaneous one. By designating one agent as the leader and the other as the follower, the mathematical complexity of the game is redefined. The follower acts as an optimization problem nested within the leader's own optimization framework.

This structure transforms the differential game into a bilevel optimization problem. The leader anticipates the follower’s reaction—which is always the optimal response given the leader’s chosen trajectory—and optimizes their own strategy accordingly. This hierarchy replaces the sensitivity of classic simultaneous solutions with a constrained optimization approach, which is often more stable to compute.

## Counterarguments / Data Gaps

While it simplifies the numerical search, the Stackelberg model assumes the leader has perfect information about the follower’s rational decision-making process. If the follower is not perfectly rational or if their objective function is misidentified, the leader’s 'optimal' strategy may fail.

## Related Concepts

[[Saddle-point equilibrium]] [[Bilevel optimization]] [[Pursuit-evasion games]]

