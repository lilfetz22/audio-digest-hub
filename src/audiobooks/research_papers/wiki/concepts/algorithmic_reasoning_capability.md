---
title: Algorithmic Reasoning Capability
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Artificial Intelligence
- Algorithmic Reasoning
- Large Language Models
---

## TLDR

Large Language Models demonstrate varying efficacy in rediscovering algorithms, excelling at procedural implementations but struggling with non-obvious, creative, or invariant-heavy logic.

## Body

The capability of LLMs to rediscover algorithms is largely segmented by the complexity and nature of the underlying logic. Simple, greedy, or divide-and-conquer algorithms, such as Dijkstra’s or Euclid’s algorithm, are well-represented within training corpora, allowing models to replicate them with high fidelity, especially when prompted with structural hints.

Conversely, algorithms requiring 'creative leaps'—such as Strassen’s matrix multiplication or the Knuth-Morris-Pratt string search—pose significant challenges. These algorithms often rely on non-obvious data structures or complex, counterintuitive invariants that are not easily surfaced through pattern matching or standard procedural generation, creating a 'creative ceiling' for current transformer architectures.

## Counterarguments / Data Gaps

Critics argue that this 'ceiling' may be an artifact of limited training data regarding the derivation processes of these specific algorithms rather than an inherent failure of the architecture. Furthermore, the reliance on external hints suggests that the models lack the latent capacity to autonomously derive these invariants from scratch.

## Related Concepts

[[Chain-of-Thought Reasoning]] [[Algorithmic Discovery]] [[System 2 Reasoning]]

