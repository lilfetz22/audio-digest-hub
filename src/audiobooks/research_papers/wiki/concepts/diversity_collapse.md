---
title: Diversity Collapse
type: concept
sources:
- 'Diversity Collapse in Multi-Agent LLM Systems: Structural Coupling and Collective
  Failure in Open-Ended Idea Generation (National University of Singapore / CUHK Shenzhen)'
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.95
categories:
- Multi-Agent Systems
- LLM Evaluation
- Creative AI
---

## TLDR

A phenomenon in multi-agent systems where agents prematurely converge on a narrow subset of the solution space instead of exploring diverse creative possibilities.

## Body

Diversity collapse occurs when an ensemble of specialized agents fails to maintain independent trajectories of thought, eventually gravitating toward a homogeneous output. Despite the individual capabilities of the underlying LLMs, the system loses its ability to generate creative, broad-ranging ideas, effectively negating the benefits of having multiple agents.

The authors attribute this failure to the 'interaction structure' of the multi-agent system rather than individual model intelligence. When agents are tightly coupled or follow suboptimal communication protocols, they reinforce each other's biases, leading to an 'echo chamber' effect where novel or divergent perspectives are filtered out in favor of consensus-seeking or safe, middle-of-the-road responses.

## Counterarguments / Data Gaps

Critics may argue that diversity collapse can be mitigated through prompting strategies like 'devil's advocate' roles or temperature scaling, suggesting the problem might be procedural rather than a fundamental structural flaw. Additionally, some argue that in certain production contexts, convergence is a desired trait rather than a failure.

## Related Concepts

[[Echo Chamber Problem]] [[Structural Coupling]] [[Collective Failure]]

