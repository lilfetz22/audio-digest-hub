---
title: Test-time Scaling
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Inference Optimization
- LLM Scaling Laws
- Agentic Workflows
---

## TLDR

The phenomenon where increasing compute resources allocated to inference-time search or planning leads to improved output quality.

## Body

Test-time scaling posits that the quality of an AI model's output is not strictly capped by its training compute. By increasing the amount of compute dedicated to exploring different paths—such as through iterative search or 'sketch-and-refine' strategies—a model can arrive at superior results than it would through a single, greedy forward pass.

This approach effectively shifts the burden of intelligence from pre-training to the inference phase. By enabling agents to perform complex reasoning or multi-step planning, systems can achieve emergent performance gains proportional to the computational budget assigned to the search process.

## Counterarguments / Data Gaps

Scaling at inference time introduces latency, which may make this approach impractical for real-time applications or high-throughput production environments. There is also a diminishing return threshold where increasing search depth or breadth provides negligible improvements in accuracy relative to the compute costs.

## Related Concepts

[[System 2 Reasoning]] [[Test-time Compute]] [[Monte Carlo Tree Search]]

