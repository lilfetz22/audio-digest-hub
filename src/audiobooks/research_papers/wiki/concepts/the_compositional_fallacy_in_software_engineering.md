---
title: The Compositional Fallacy in Software Engineering
type: concept
sources:
- 'More Is Different: Toward a Theory of Emergence in AI-Native Software Ecosystems,
  by Daniel Russo'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Software Engineering
- AI-Native Software
- Systems Theory
---

## TLDR

The traditional, yet increasingly flawed, assumption that verifying every individual unit or module guarantees the overall soundness of an entire software system.

## Body

The "compositional assumption" has been the foundational philosophy of software engineering for decades. It posits that a complex system can be fully understood, built, and verified by breaking it down into its constituent parts, testing each part individually, and assembling them together.

This philosophy underpins standard software quality assurance practices, including unit testing, static analysis, and code review. If every unit, function, and module behaves as expected in isolation, the compositional assumption dictates that the final integrated system will also be sound.

However, this assumption becomes a "fallacy" in the context of highly complex or emergent systems, such as AI-native software ecosystems. In these environments, the interaction between components can produce unexpected, emergent behaviors that are impossible to predict simply by analyzing the individual modules in isolation.

## Counterarguments / Data Gaps

While emergent behaviors in AI systems challenge the compositional assumption, unit testing and modular verification remain critical for catching baseline logical errors and regressions. Complete abandonment of compositional verification would lead to unmaintainable codebases; rather, it needs to be supplemented with robust integration, system-level, and behavioral testing.

## Related Concepts

[[Emergence]] [[Unit Testing]] [[Systems Thinking]] [[Integration Testing]]

