---
title: System Latency Jacobian
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.85
categories:
- Performance Profiling
- Systems Engineering
---

## TLDR

An analytical concept used to measure how a system's output latency changes with respect to its input batch size.

## Body

In the context of machine learning systems engineering, the "Jacobian" of the system refers to the rate of change of output latency with respect to the input batch size. It acts as a derivative measure of system stability and scalability under varying loads.

A highly optimized inference stack will exhibit a stable Jacobian, meaning that as the batch size scales up, the latency increases predictably and manageably, allowing for high consistent throughput (e.g., thousands of samples per second). Conversely, an unoptimized baseline system will struggle as batch sizes increase, showing an unstable or exponentially degrading latency curve.

## Counterarguments / Data Gaps

Using the term "Jacobian" in this context is a loose, metaphorical borrowing from multi-variable calculus rather than a strict mathematical application. Treating latency strictly as a function of batch size risks oversimplifying complex system bottlenecks, ignoring other highly variable factors like network congestion, memory bandwidth saturation, and CPU-GPU transfer bottlenecks.

## Related Concepts

[[Adaptive Batching]]

