---
title: Coroutine-based Multi-tasking
type: concept
sources:
- NanoCockpit paper transcript
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Operating Systems
- Embedded Systems
- Software Engineering
---

## TLDR

A lightweight, stackless execution model that replaces traditional RTOS to enable rapid task switching and maximize CPU utilization.

## Body

**Coroutine-based multi-tasking** is a lightweight execution strategy utilized to replace traditional, memory-heavy Real-Time Operating Systems (RTOS). By eliminating the need for dedicated memory stacks for every task, it provides a highly efficient "stackless" coroutine layer.

This architecture allows the system to pause operations that are waiting on external events—such as waiting for a camera frame to capture—and immediately switch to executing another active task, like running a machine learning inference.

The primary advantage of this approach is its extremely low latency context switching, which can operate in under 10 microseconds. This ensures that the processor remains fully utilized (working at 100% capacity) rather than sitting idle during I/O operations.

## Counterarguments / Data Gaps

While highly efficient for memory-constrained environments, stackless coroutines can increase software complexity, as developers must manually manage state across asynchronous yields. Furthermore, lacking a full RTOS may limit the availability of standard scheduling features, preemptive multitasking, and strict real-time guarantees required for certain deterministic safety-critical systems.

## Related Concepts

[[Real-Time Operating System (RTOS)]] [[Stackless Coroutines]] [[Context Switching]]

