---
title: SPGM (Sequential Proximal Gradient Method)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Optimization
- Machine Learning Algorithms
- Mathematical Optimization
---

## TLDR

A dynamic optimization algorithm that improves upon static worst-case bounds by leveraging historical data to adapt to local function geometry.

## Body

SPGM operates by maintaining a bundle of information from past iterations, functioning similarly to L-BFGS but within a proximal gradient framework. By solving subproblems at every optimization step, the algorithm is able to infer the underlying structure of the function, allowing it to capitalize on 'easy' paths in the optimization landscape.

Unlike traditional static methods like OGM, which rely on a flat, universal worst-case guarantee, SPGM provides a dynamic error bound that tightens as more data is processed. This adaptive behavior makes it particularly effective for structured, non-adversarial problem domains where local geometry is more favorable than global worst-case scenarios.

## Counterarguments / Data Gaps

While SPGM outperforms classical methods on structured problems, its reliance on history-dependent subproblems may increase computational complexity compared to simpler first-order methods. Additionally, its performance gain is predicated on the assumption that the optimization landscape is not purely adversarial.

## Related Concepts

[[OGM (Optimal Gradient Method)]] [[L-BFGS]] [[Proximal Gradient Descent]]

