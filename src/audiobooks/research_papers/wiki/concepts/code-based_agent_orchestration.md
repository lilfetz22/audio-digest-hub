---
title: Code-Based Agent Orchestration
type: concept
sources:
- LangGraph
- CrewAI
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- AI Agents
- Software Engineering
- Orchestration Frameworks
---

## TLDR

A structured approach to building AI agents using software frameworks to define control flow, which often tangles logic and becomes brittle.

## Body

Code-based orchestration involves using explicit software frameworks—such as LangGraph or CrewAI—to define the control flow, state management, and tool interactions of AI agents. This paradigm applies traditional software engineering rigor to agent development, allowing for more predictable, structured execution compared to purely prompt-driven approaches.

However, these frameworks frequently suffer from a tight coupling between the application's core business logic and the agent's control flow. As the complexity of the agentic system scales, the codebase can quickly become brittle, difficult to maintain, and hard to visually conceptualize or debug.

## Counterarguments / Data Gaps

While providing necessary structure, code-based orchestration frameworks can over-constrain the natural reasoning flexibility of LLMs. Additionally, the tight coupling of logic and control flow often leads to technical debt, requiring significant refactoring whenever agent behaviors or underlying foundational models are updated.

## Related Concepts

[[AgentSPEX]] [[Reactive Prompting]] [[LangGraph]] [[CrewAI]]

