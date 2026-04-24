---
title: Governance-to-Action Closure Gap
type: concept
sources:
- 'Beyond Task Success: An Evidence-Synthesis Framework for Evaluating, Governing,
  and Orchestrating Agentic AI (Koch and Wellbrock)'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- AI Governance
- AI Safety
- Agentic AI
- Compliance
---

## TLDR

The disconnect between high-level AI governance policies and the specific, low-level actions executed by autonomous multi-step agents.

## Body

As the AI landscape transitions from simple, single-turn Large Language Models to complex, multi-step agents capable of planning and executing external tool calls, a significant oversight in evaluation has emerged. Historically, the industry has focused heavily on 'Task Success'—measuring whether an agent ultimately arrived at the correct answer or outcome.

Koch and Wellbrock argue that this outcome-centric view creates a 'Governance-to-Action closure gap'. While high-level governance frameworks (such as those from NIST or ISO) define broad safety and compliance rules, and traditional benchmarks measure final success, there is a missing operational link. There is no unified mechanism to ensure that the actual *path* the agent took—the sequence of specific, low-level tool actions—was safe, compliant, and aligned with those high-level rules.

Closing this gap requires moving beyond binary success metrics to develop evidence-synthesis frameworks. These frameworks must bind abstract governance mandates directly to agentic tool execution, allowing human overseers to prove retroactively that an agent followed permissible and safe trajectories throughout its entire operational lifecycle.

## Counterarguments / Data Gaps

Implementing strict path-based compliance could severely limit the emergent problem-solving capabilities and flexibility that make autonomous agents useful in the first place. Furthermore, defining, tracking, and verifying every possible safe trajectory in highly complex, open-ended environments may be computationally prohibitive or practically impossible.

## Related Concepts

[[Task Success Metrics]] [[SuperIgor (Self-Improving Agent Loop)]] [[Multi-step Agents]]

