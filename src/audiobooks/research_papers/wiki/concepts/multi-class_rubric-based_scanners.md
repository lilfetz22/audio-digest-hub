---
title: Multi-class Rubric-based Scanners
type: concept
sources:
- Seven simple steps for log analysis in AI systems
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.99
categories:
- Model Evaluation
- AI Safety
- Benchmarking
---

## TLDR

Evaluating complex model behaviors requires multi-class, rubric-based scanners validated against human judgment rather than simple binary checks or keyword matching.

## Body

When evaluating AI agents on complex tasks, such as cybersecurity Capture The Flag (CTF) challenges, simple keyword matching (e.g., searching for "I can't") is highly ineffective. Modern language models use subtle, varied language to refuse tasks, which easily evades basic programmatic checks and binary classifications.

To reliably detect these behaviors, evaluators must transition to multi-class, rubric-based systems. For example, replacing a simple "refusal vs. no-refusal" binary with a four-tier scale—No, Partial, Indirect, and Critical refusal—allows for much higher precision. By training scanners with these specific anchors, evaluators can achieve near-perfect accuracy, with the authors reporting an F1 score of 0.998.

A critical requirement for these scanners is the existence of a validation set. Without benchmarking the scanner's performance against human judgment, the scanner's outputs are ultimately unreliable and akin to a "random number generator."

Furthermore, transitioning to categorical definitions rather than rigid string matching allows these advanced scanners to evaluate outputs based on highly nuanced criteria. Rigorously validating these scanners against human-labeled ground truth ensures the evaluation system accurately captures the full spectrum of models' responses. This comprehensive approach is essential for generating reliable, actionable performance metrics and ensuring safer AI deployments.

## Counterarguments / Data Gaps

Creating a multi-class rubric and a human-annotated validation set is labor-intensive and time-consuming, making it difficult to scale across rapidly changing model behaviors. Furthermore, human judgment itself can be subjective, potentially introducing human bias into the "ground truth" validation set used to score the scanner. Additionally, as models evolve and their language patterns change over time, rubrics and datasets must be continuously refreshed to prevent evaluation drift and maintain system accuracy.

## Related Concepts

[[Keyword Matching]] [[Ground Truth Validation]] [[Agent Refusals]]

