---
title: Coarse-to-Fine 1D Ordered Tokenization
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Computer Vision
- Generative Models
- Inference Optimization
---

## TLDR

A structural approach to image generation that sequences data from global structure to fine detail, enabling meaningful intermediate states for search algorithms.

## Body

Traditional image generation models often process images as a flat 2D grid, which results in incoherent intermediate noise when viewed during the generation process. This approach renders traditional search techniques—like Beam Search—ineffective because evaluators cannot determine if the partial output is moving toward a successful result.

The coarse-to-fine method reframes the generation sequence into a 1D ordered token stream. Similar to a human sketching a portrait, the model is trained to generate low-resolution, global information first, followed by incremental refinements. This ensures that the intermediate states are semantic, human-readable representations of the final product rather than stochastic noise.

By forcing the model to commit to high-level structures early, the sequence becomes traversable. Verifiers can evaluate these structural 'sketches' to prune low-quality paths early in the inference process, significantly improving the efficacy of test-time search.

## Counterarguments / Data Gaps

While this method improves searchability, it may introduce inductive biases that restrict the model's ability to represent certain types of fine-grained, non-hierarchical, or highly irregular visual patterns. Furthermore, enforcing a specific sequence order can limit the flexibility of training data pipelines and may require more complex architectural adaptations to standard transformer blocks.

## Related Concepts

[[Test-time Search]] [[Beam Search]] [[Latent Diffusion Models]] [[Autoregressive Generation]]

