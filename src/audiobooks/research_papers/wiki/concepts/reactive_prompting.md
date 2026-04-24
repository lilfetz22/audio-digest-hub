---
title: Reactive Prompting
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.9
categories:
- Prompt Engineering
- AI Agents
---

## TLDR

An agent design paradigm where an LLM is given a goal and tools, and autonomously determines its execution path.

## Body

Reactive prompting is a flexible approach to building AI agents where the underlying Large Language Model (LLM) is provided with an overarching goal and a set of tools. The model is then left to autonomously deduce the necessary steps, tool calls, and execution path required to achieve that goal.

While this paradigm offers immense flexibility and requires minimal upfront structural coding, it operates largely as a black box. The lack of explicit control flow means the agent's decision-making process is opaque, making it notoriously difficult for developers to debug when the agent hallucinates, enters infinite loops, or fails to complete the assigned task.

## Counterarguments / Data Gaps

The primary limitation of reactive prompting is its severe lack of debuggability and predictability. Because the control flow relies entirely on the LLM's real-time generation, it is highly susceptible to prompt variations, context window limits, and model updates, making it risky for mission-critical engineering applications.

## Related Concepts

[[AgentSPEX]] [[Code-Based Agent Orchestration]]

