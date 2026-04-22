---
title: Trajectory-Based Optimization
type: concept
sources:
- Pang, Y. et al. (Research on Trajectory-based optimization in TMA)
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.98
categories:
- Air Traffic Control
- Optimization
- Operations Research
---

## TLDR

A paradigm shift in operational management that prioritizes physically flyable geometric paths and speed profiles over abstract time-based or node-link network models.

## Body

Trajectory-based optimization moves beyond traditional air traffic control scheduling, which often treats aircraft paths as abstract nodes and edges in a network. While node-link models are computationally efficient at solving time-delay puzzles, they frequently fail to account for the physical realities of flight dynamics, such as turn radii, aircraft performance constraints, and fuel-efficient speed profiles.

By integrating the specific geometric paths and speed profiles into the optimization process, this framework ensures that scheduled arrival times are not just theoretically calculated, but actually achievable. This includes managing complex maneuvers like base-leg extensions and segment-wise velocity adjustments required to maintain air traffic separation standards within a Terminal Maneuvering Area (TMA).

(New research adds): Trajectory-based optimization treats the physical geometry of an agent's path as a first-class citizen in the optimization process. By modeling the full spatial path rather than just temporal intervals, this approach captures the operational reality of movement, which is critical for complex terminal or robotic environments. This method mirrors human controller decision-making, where the spatial configuration is as vital as arrival times. By integrating these geometric constraints into the formal optimization framework, models can achieve high-fidelity alignment between simulation and real-world execution.

## Counterarguments / Data Gaps

The primary limitation of this approach is increased computational complexity compared to traditional network-based models. Calculating flyable trajectories for large fleets of aircraft in real-time requires significantly higher processing power, which may hinder its scalability in extremely congested airspace scenarios. Additionally, these models may struggle in highly dynamic environments where the geometry of the workspace changes rapidly or unpredictably.

## Related Concepts

[[Stochastic Optimization]] [[Formal Verification]] [[Geometric Modeling]]

