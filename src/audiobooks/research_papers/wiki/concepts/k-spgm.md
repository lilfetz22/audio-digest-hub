---
title: k-SPGM
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Computational Optimization
- Memory-Efficient Algorithms
---

## TLDR

A limited-memory variant of SPGM that maintains linear computational scaling while preserving the adaptive advantages of the full algorithm.

## Body

The k-SPGM variant addresses the potential computational overhead of maintaining a full history of past iterations. By limiting the 'bundle' of information to a fixed size (k), the algorithm ensures that memory and computation requirements scale linearly with the number of dimensions in the problem.

Despite this limitation in stored information, k-SPGM retains the core benefit of SPGM: the ability to adapt to the local geometry of the function during runtime. This makes it a practical choice for high-dimensional AI training tasks where full-history storage would be computationally prohibitive.

## Counterarguments / Data Gaps

Limiting the memory to 'k' iterations effectively imposes a windowing function on the algorithm's 'memory.' If the optimization trajectory requires information from deeper in the past than k steps to navigate complex geometry, the performance may degrade compared to the full-history version.

## Related Concepts

[[SPGM]] [[L-BFGS]]

