---
title: Test-Time Search
type: concept
sources:
- Ordered Tokens Enable Efficient Test-Time Search
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- AI Agents
- Inference Optimization
- Generative Models
---

## TLDR

A technique that empowers autoregressive models to perform deliberative planning and evaluation of output candidates by exploring multiple generation paths mid-sequence to prune poor outputs before completion.

## Body

Test-time search addresses the 'greediness' of standard autoregressive models by allowing them to look ahead or traverse a search space during inference. Instead of simply selecting the most probable next token, the model evaluates multiple branches, enabling it to navigate complex tasks that require foresight or error correction.

This is particularly relevant for AI agents, where the consequences of a single token choice can cascade into inaccurate or unsafe outcomes. By separating the 'thinking' phase from the 'speaking' phase, test-time search transforms static generators into dynamic problem solvers.

[NEW ADDITIONS] Test-time search refers to the application of search algorithms (such as Beam Search or Best-of-N) during the inference phase of a generative model. Instead of a single pass of sequential generation, the model considers multiple potential futures and selects the most promising one based on an external or internal verifier. In standard architectures, the lack of semantic content in intermediate tokens prevents effective search, as there is no reliable signal to guide the verifier. By enabling structural coherence through techniques like coarse-to-fine tokenization, test-time search becomes a viable strategy to enhance reasoning and output quality in complex generative tasks.

## Counterarguments / Data Gaps

Implementing test-time search adds significant latency to inference, as generating multiple candidate paths and evaluating them requires more compute cycles. This overhead can be a major barrier for real-time applications, making it necessary to balance the depth of the search with the latency constraints of the specific use case. Furthermore, test-time search significantly increases the compute budget per request and may lead to diminishing returns if the verifier is not perfectly calibrated to the model's output distribution.

## Related Concepts

[[Beam Search]] [[Best-of-N]] [[Tree Search]] [[Pruning]]

