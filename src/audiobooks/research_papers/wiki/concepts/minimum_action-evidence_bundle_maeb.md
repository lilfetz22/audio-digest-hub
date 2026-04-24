---
title: Minimum Action-Evidence Bundle (MAEB)
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Auditing
- Logging
- Compliance
- Data Schemas
---

## TLDR

A practical logging schema that dictates the essential data points required to create a robust audit trail for risky, state-changing AI actions.

## Body

The Minimum Action-Evidence Bundle (MAEB) is a standardized schema designed to ensure accountability and traceability in AI systems. It defines the exact artifacts and data points that must be logged whenever an AI system performs a risky or state-changing action.

Often conceptualized as an "audit trail in a box," the MAEB requires the capture of specific contextual and operational data. This includes the identity of the actor, the specific policy IDs governing the action, snapshots of the system state prior to the action, and the exact tool parameters utilized. This structured approach to logging ensures that there is sufficient evidence for the Assurance layer of the system.

## Counterarguments / Data Gaps

Implementing the MAEB requires capturing and storing extensive pre-action state snapshots and parameter data, which could lead to significant data storage overhead and potential performance degradation in high-throughput systems. Additionally, capturing this level of granular detail might inadvertently log sensitive or personally identifiable information (PII), creating new security and privacy compliance risks.

## Related Concepts

[[The Four-Layer Framework]]

