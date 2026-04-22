---
title: First-on-Final-First-Serve (FOFFS)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Air Traffic Management
- Logistics Optimization
- Sequencing Algorithms
---

## TLDR

An air traffic sequencing strategy that prioritizes arrival order based on aircraft position on the final approach rather than initial entry time.

## Body

FOFFS is an arrival management heuristic that sequences aircraft based on their proximity to the final approach phase. Unlike traditional First-Entry-First-Serve (FEFS) models, which adhere strictly to the time of entry into the terminal radar approach control (TRACON) airspace, FOFFS leverages the specific geometric asymmetries inherent in different arrival gates.

By prioritizing aircraft that are further along the path to landing, the system reduces unnecessary path stretching and orbital holding patterns. This approach inherently aligns with the objective of optimizing runway capacity and minimizing fuel burn, as it reduces the need for late-stage sequencing adjustments.

## Counterarguments / Data Gaps

While FOFFS improves throughput, it may introduce inequity for aircraft that enter the system early but are relegated to secondary status due to their approach geometry. Additionally, its performance relies heavily on the accuracy of real-time trajectory predictions, which can be degraded by environmental variables like wind or speed variability.

## Related Concepts

[[FEFS]] [[Arrival Management]] [[TRACON]]

