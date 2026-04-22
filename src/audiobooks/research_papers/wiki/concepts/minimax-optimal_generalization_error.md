---
title: Minimax-Optimal Generalization Error
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Statistical Learning Theory
- Generative Modeling
---

## TLDR

A theoretical guarantee that the error of a learned score function decreases at the fastest possible rate relative to sample size.

## Body

Minimax optimality establishes a fundamental lower bound on the error that any estimator can achieve for a given statistical problem. In the context of score-based generative models, this means the proposed training procedure achieves the best possible convergence rate allowed by information theory.

By following the prescribed early-stopping rule, the discrepancy between the model's learned score function and the true data score function is minimized. This provides a rigorous mathematical foundation that replaces heuristic trial-and-error, ensuring that as more data is provided, the model's performance improves in a predictable, optimal fashion.

## Counterarguments / Data Gaps

While minimax optimality is mathematically elegant, it often describes the 'best-case' asymptotic behavior. In practice, the constant factors hidden by big-O notation can make these theoretical bounds less relevant for small-scale, real-world datasets.

## Related Concepts

[[Score-based Generative Models]] [[Generalization Error]] [[Non-parametric Estimation]]

