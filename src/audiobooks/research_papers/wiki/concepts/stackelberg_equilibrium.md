---
title: Stackelberg Equilibrium
type: concept
sources:
- A Numerical Analysis for Pursuit-Evasion Games under the Stackelberg Equilibrium
  by Kazuhiro Horie
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Control Theory
- Game Theory
- Optimization
---

## TLDR

A strategic model for differential games where a leader acts first and a follower optimizes their response to the leader's strategy, creating a hierarchical decision structure.

## Body

In the context of differential games, a Stackelberg equilibrium moves away from the simultaneous decision-making of Nash or saddle-point equilibria. Instead, it assumes a sequential hierarchy where the 'leader' commits to a strategy, and the 'follower' observes this choice before selecting their own optimal response. This approach is particularly useful in systems where there is a natural priority or sequence of control actions, such as in aerospace intercept scenarios.

Mathematically, this transforms the problem into a bilevel optimization task. The leader must anticipate the follower's reaction, effectively embedding the follower's optimal control problem as a constraint within the leader's own optimization framework. By structuring the game this way, the inherent unpredictability of simultaneous-move equilibrium search is mitigated, allowing for more stable computational modeling.

## Counterarguments / Data Gaps

The primary limitation of the Stackelberg approach is the assumption of a rigid hierarchy; in real-world scenarios, players may not always adhere to a leader-follower dynamic, potentially rendering the equilibrium irrelevant. Additionally, the computational complexity of solving bilevel problems is significant, as the follower's optimality condition must be satisfied at every step of the leader's iteration.

## Related Concepts

[[Nash Equilibrium]] [[Bilevel Optimization]] [[Differential Games]]

