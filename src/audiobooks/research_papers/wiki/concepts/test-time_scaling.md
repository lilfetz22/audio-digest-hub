---
title: Test-time Scaling
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Inference Optimization
- LLM Scaling Laws
- Agentic Workflows
---

## TLDR

The phenomenon where increasing computational resources, such as search or exploration, during inference leads to improved model output quality by enabling dynamic reasoning beyond the constraints of training compute.

## Body

Test-time scaling posits that the quality of an AI model's output is not strictly capped by its training compute. By increasing the amount of compute dedicated to exploring different paths—such as through iterative search or 'sketch-and-refine' strategies—a model can arrive at superior results than it would through a single, greedy forward pass. This approach effectively shifts the burden of intelligence from pre-training to the inference phase. By enabling agents to perform complex reasoning or multi-step planning, systems can achieve emergent performance gains proportional to the computational budget assigned to the search process.

[ADDITION] Test-time scaling suggests that performance is not strictly bounded by the size of the model's parameters or the amount of data used during training. By allowing a model to explore multiple potential paths during inference—often using techniques like lookahead, iterative planning, or tree search—the system can reach better outcomes than the raw model could produce in a single forward pass. This allows models to demonstrate 'reasoning-like' capabilities by 'thinking' more before finalizing an output. It shifts the burden of intelligence from solely training-time parameter updates to dynamic, context-aware exploration at the moment of query.

## Counterarguments / Data Gaps

Scaling at inference time introduces latency, which may make this approach impractical for real-time applications or high-throughput production environments. There is also a diminishing return threshold where increasing search depth or breadth provides negligible improvements in accuracy relative to the compute costs. [ADDITION] Furthermore, test-time scaling assumes that the model can be guided by an effective objective function or verifier, which may not exist for all domains, potentially limiting its applicability.

## Related Concepts

[[System 2 Thinking]] [[Scaling Laws]] [[Search-augmented Generation]]

