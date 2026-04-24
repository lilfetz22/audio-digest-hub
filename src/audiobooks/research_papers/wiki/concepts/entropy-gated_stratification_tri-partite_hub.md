---
title: Entropy-Gated Stratification (Tri-Partite Hub)
type: concept
sources:
- 'Prism: An Evolutionary Memory Substrate for Multi-Agent Open-Ended Discovery'
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.98
categories:
- Information Theory
- Memory Management
- Data Stratification
---

## TLDR

A memory management mechanism that categorizes and stores agent knowledge into three tiers—Skills, Notes, and Attempts—based on the information's entropy.

## Body

Entropy-Gated Stratification is the core methodological innovation of the Prism framework, operating through a structure known as the Tri-Partite Hub. Instead of treating all agent memories equally, this mechanism uses information entropy to route and store data across a three-tier funnel, optimizing both retrieval speed and storage efficiency.

Tier 1 consists of **Skills**, which are low-entropy, highly repeatable procedures. Because these form the foundational behaviors of agent performance, they are kept in an "always-loaded" state. Tier 2 comprises **Notes**, which are medium-entropy observations. These are stored in a graph structure and are only retrieved via semantic search when contextually relevant.

Tier 3 is dedicated to **Attempts**, representing high-entropy, raw logs of trial-and-error. To conserve active memory, these logs are kept in cold storage. They are only accessed when an agent's "Value-of-Information" policy determines that reviewing these raw logs is necessary to resolve a specific uncertainty.

## Counterarguments / Data Gaps

Relying on an entropy metric and a "Value-of-Information" policy introduces potential computational bottlenecks, as the system must continuously calculate these values to route data. Misclassification of entropy could lead to critical trial-and-error "Attempts" being trapped in cold storage, or useless "Skills" clogging the active memory limit.

## Related Concepts

[[Prism (Evolutionary Memory Substrate)]] [[Value-of-Information Policy]] [[Semantic Search]]

