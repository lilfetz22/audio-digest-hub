---
title: Trajectory-Based Optimization
type: concept
sources:
- Yutian Pang et al.
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

---

### Update (2026-04-22)

Traditional air traffic control scheduling relies on node-link abstractions, which treat airspace as a network of fixed points. While efficient for routing, these models often fail to account for the physical constraints of flight, such as speed profiles and maneuverability. This leads to scheduling plans that are theoretically sound but practically difficult for pilots to execute without adjustments.

Trajectory-based optimization shifts the focus from scheduling abstract arrival times to generating specific, flyable paths. By calculating base-leg extensions and segment-wise speed adjustments, this framework ensures that the aircraft can physically meet separation requirements. This integration bridges the gap between high-level scheduling and low-level flight control.

**New counterarguments:** The primary limitation of trajectory-based optimization is computational complexity, as calculating physics-informed paths for multiple aircraft simultaneously requires significantly more resources than simple node-link scheduling. Additionally, this approach may be sensitive to real-time variables like sudden weather shifts or unexpected turbulence, which can quickly render optimized geometric paths obsolete.

---

### Update (2026-04-22)

Trajectory-based optimization focuses on the continuous path taken by an agent or system rather than just its arrival or departure time at specific nodes. This method allows for more fluid operational management, enabling systems to dynamically adjust speed and pathing to maintain safety and efficiency.

In the context of terminal management, this transition mirrors human decision-making, where controllers visualize and adjust the entire path of a vehicle rather than just scheduling static time slots. This allows for the integration of real-time environmental factors, leading to a more holistic control strategy.

**New counterarguments:** Trajectory-based models are inherently more difficult to solve than time-based models because they exist in a continuous state space rather than a discrete one. The added dimensionality can make finding global optima more challenging and may necessitate heuristic or approximate solutions rather than exact ones.

