---
title: Reason-Invoke-Observe-Critique (RIOC) Loop
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.92
categories:
- Agentic Reasoning
- Multi-Agent Collaboration
---

## TLDR

An iterative reasoning cycle that structures agent behavior by alternating between hypothesis generation, action execution, observation, and critical self-evaluation.

## Body

The RIOC loop serves as the operational engine for EvoMaster agents, enforcing a disciplined progression for every task. The agent begins by reasoning through a hypothesis, proceeds to invoke necessary tools or actions, observes the outcomes, and concludes with a critical reflection stage.

This loop is further enhanced by multi-agent collaboration, where distinct roles such as a 'Solver' and a 'Critic' engage in a debate to refine hypotheses. This structured friction prevents premature conclusions and ensures that the agent's final output is filtered through an adversarial validation process.

## Counterarguments / Data Gaps

The RIOC loop, particularly with multi-agent debate, can significantly increase the number of inference calls required, leading to higher computational costs and slower execution times. Additionally, the effectiveness of the 'Critic' is highly dependent on the system prompt and the model's inherent ability to self-correct.

## Related Concepts

[[Chain-of-Thought]] [[Reflexion]] [[Multi-Agent Debate]]

