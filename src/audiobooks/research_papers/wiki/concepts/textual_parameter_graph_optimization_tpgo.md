---
title: Textual Parameter Graph Optimization (TPGO)
type: concept
sources:
- 'Learning to Evolve: A Self-Improving Framework for Multi-Agent Systems via Textual
  Parameter Graph Optimization (Alibaba Future Living Lab)'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Multi-Agent Systems
- Prompt Engineering
- Automated Optimization
- Graph-based Models
---

## TLDR

A self-improving framework for multi-agent systems that uses graph-based structural awareness to optimize agent configurations and remember past mistakes.

## Body

Textual Parameter Graph Optimization (TPGO) is a self-improving framework developed by Alibaba's Future Living Lab to optimize Multi-Agent Systems (MAS). It is designed to solve the 'Agent Engineering' bottleneck, a tedious process where developers traditionally have to manually tweak system prompts in a trial-and-error workflow to fix agent behaviors.

Current automated optimization methods typically apply a 'flat' approach, treating an agent's entire configuration as a single, monolithic block of text. This lack of structural awareness means that when an agent fails—such as a breakdown in a tool-use protocol or a logic gap between two agents—the optimizer struggles to pinpoint the exact location of the failure.

TPGO addresses this by introducing structural awareness through a graph-based representation of textual parameters. Furthermore, unlike static optimizers that constantly relearn from scratch without remembering past mistakes, TPGO's architecture allows the multi-agent system to retain optimization history and continuously evolve.

## Counterarguments / Data Gaps

While the transcript highlights the flaws of 'flat' optimizers—namely their lack of memory and structural awareness—graph-based optimization frameworks like TPGO inherently require more complex setup to define the nodes and edges of the agent architecture. Additionally, even with structural awareness, highly complex logic gaps between autonomous agents may still require human intervention if the automated optimizer misinterprets the root cause of a failure.

## Related Concepts

[[Flat Automated Optimization]] [[Agent Engineering]]

