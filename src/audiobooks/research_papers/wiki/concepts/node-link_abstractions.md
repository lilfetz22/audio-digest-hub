---
title: Node-Link Abstractions
type: concept
sources:
- Yutian Pang et al.
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Operations Research
- Network Theory
---

## TLDR

A legacy modeling approach in air traffic control that simplifies airspace into networks of points and edges to solve time-delay scheduling problems.

## Body

Node-link models represent the Terminal Maneuvering Area (TMA) as a graph, where aircraft progress from node to node based on predefined edge constraints. These models are favored in industry for their computational efficiency, as they reduce a complex 4D trajectory problem into a discrete time-delay puzzle.

While effective for high-level flow management, these models operate on the assumption that a time-over-waypoint target is achievable for any aircraft. They lack the granularity to verify if a flight can actually achieve a specific speed or path extension to reach that waypoint on time, leading to gaps between scheduled goals and operational reality.

## Counterarguments / Data Gaps

The main counterargument is that node-link abstractions provide the only computationally feasible method for managing large-scale airspace with hundreds of simultaneous flights. More granular physical modeling is often too slow to run in real-time, making node-link models a necessary trade-off for speed and scalability.

## Related Concepts

[[Air Traffic Control]] [[Trajectory-Based Optimization]]

