---
title: Physical Isolation in Multi-Agent Systems
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- AI Safety
- System Architecture
- Security
---

## TLDR

Enforcing strict filesystem or container-level isolation between agents is necessary because capable LLMs can easily bypass convention-based software barriers.

## Body

When building multi-agent systems—particularly those involving independent evaluator and executor agents—maintaining strict separation is crucial for objective outcomes. Relying on software conventions, such as hiding files with a dot-prefix, is insufficient because highly capable models can deduce and bypass these superficial barriers.

To ensure true independence, isolation must be enforced at the infrastructure level. This means utilizing separate filesystems, sandboxed environments, or distinct containers for different agents. This prevents cross-contamination of context and ensures that evaluation agents remain entirely objective and uninfluenced by the executor's hidden states.

## Counterarguments / Data Gaps

Strict physical isolation increases infrastructure overhead, deployment complexity, and latency, as agents must now communicate over network protocols or highly restricted shared interfaces rather than executing simple local file reads.

## Related Concepts

[[Dynamic Agentic Evaluation]]

