---
title: End-state Grading
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 1.0
categories:
- AI Evaluation
- Agentic Frameworks
---

## TLDR

An evaluation methodology that verifies the success of an AI agent based solely on the final state of the environment rather than the specific steps taken to achieve it.

## Body

End-state grading shifts the focus of agent evaluation from process to outcome. Instead of judging an agent based on trace logs or step-by-step reasoning, researchers utilize programmatic assertions that function similarly to unit tests for the environment's database.

By checking if the final data state matches the desired outcome, this method ensures that agents are functionally effective rather than just rhetorically convincing. It allows for a more robust assessment of real-world utility where the specific methodology used to achieve a task is secondary to the correctness of the final result.

## Counterarguments / Data Gaps

A primary limitation is that it ignores the safety or efficiency of the path taken; an agent could achieve the correct end-state through risky or highly inefficient actions that might be dangerous in a production environment. Additionally, it provides little diagnostic feedback to developers on where exactly the agent failed during its reasoning process.

## Related Concepts

[[Unit Testing]] [[Task Planning]]

