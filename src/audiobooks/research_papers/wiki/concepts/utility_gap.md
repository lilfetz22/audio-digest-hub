---
title: Utility Gap
type: concept
sources: []
created: '2026-04-23'
updated: '2026-04-23'
confidence: 0.9
categories:
- LLM Evaluation
- Agent Engineering
---

## TLDR

The divergence between high tool-usage frequency and actual performance improvement in LLM-based agents.

## Body

The utility gap describes a scenario where an agent frequently invokes external tools or skill libraries without realizing a measurable improvement in task success rates. This suggests that the agent's decision-making process regarding 'when' and 'how' to use a tool is decoupled from the tool's actual efficacy in the given context.

This gap indicates that frequent tool-calling might be indicative of a model's reliance on superficial patterns rather than a true understanding of utility. Builders must look beyond raw tool-usage metrics and focus on the performance delta following the introduction of new capabilities to verify that those capabilities are providing genuine value.

## Counterarguments / Data Gaps

Some researchers suggest that a high utility gap might simply be a 'discovery phase' where the model is exploring a new toolset. They argue that performance metrics might lag behind usage as the model learns to effectively integrate the new skills over time.

## Related Concepts

[[Skill Interference]] [[Tool Use]]

