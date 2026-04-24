---
title: The ODTA Test
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Diagnostic Tools
- System Controls
- Risk Management
---

## TLDR

A diagnostic tool used to determine the appropriate placement of system controls by evaluating Observability, Decidability, Timeliness, and Attestability.

## Body

The ODTA Test is a diagnostic framework used by system architects to determine exactly where a specific control or requirement should be placed within an AI system's lifecycle. It forces designers to ask four critical questions about any given requirement: Observability (can the event be seen?), Decidability (is the rule clear and crisp?), Timeliness (can action be taken fast enough?), and Attestability (can the action be proven later?).

By evaluating requirements against these four criteria, teams can avoid placing inappropriate burdens on runtime systems. If a requirement fails the ODTA test, it indicates that the control should not be handled by the runtime orchestrator. Instead, it must be shifted left to the design phase or escalated to a human-in-the-loop review process.

## Counterarguments / Data Gaps

The ODTA test assumes that "decidability" and "timeliness" are binary or easily quantifiable metrics, whereas in complex AI deployments, these factors often exist on a spectrum. Furthermore, shifting controls to a human-in-the-loop process when they fail the ODTA test can create bottlenecks, significantly impeding the scalability and autonomous benefits of the AI system.

## Related Concepts

[[The Four-Layer Framework]] [[Human-in-the-loop]]

