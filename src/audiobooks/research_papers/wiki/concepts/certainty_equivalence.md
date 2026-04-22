---
title: Certainty Equivalence
type: concept
sources:
- 'Li, Yuchao and Bertsekas, Dimitri, ''Semilinear Dynamic Programming: Analysis,
  Algorithms, and Certainty Equivalence Properties'''
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Stochastic Control
- Decision Theory
---

## TLDR

A principle where an optimal control policy is derived by treating uncertain variables as if they were known expected values, simplifying the decision-making process.

## Body

Certainty equivalence is a property in stochastic optimal control where the optimal decision rule in the presence of uncertainty is identical to the rule that would be chosen if the uncertain variables were perfectly known (usually replaced by their expected values). In the context of the paper, this property is the 'holy grail' because it allows for the decoupling of estimation and control.

By ensuring that certain dynamic programming problems satisfy this property, the research facilitates the creation of agents that act optimally without requiring full stochastic modeling at every step of the decision loop. This significantly reduces the computational burden when deploying agents into physical or uncertain environments.

## Counterarguments / Data Gaps

Certainty equivalence is often suboptimal or even unstable in systems with high levels of non-additive noise or significant nonlinearities. In many practical settings, ignoring the variance of the uncertainty—as certainty equivalence does—can lead to poor performance or safety failures.

## Related Concepts

[[Linear-Quadratic Control]] [[Stochastic Optimization]] [[Optimal Policy]]

