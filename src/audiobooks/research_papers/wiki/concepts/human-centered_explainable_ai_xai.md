---
title: Human-Centered Explainable AI (XAI)
type: concept
sources:
- Using Learning Theories to Evolve Human-Centered XAI (CHI '23)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Explainable AI (XAI)
- Human-Computer Interaction (HCI)
- Model Interpretability
---

## TLDR

As AI models become increasingly complex, traditional technical explanations become intractable, requiring a shift toward understanding how humans actually process and learn from these explanations.

## Body

The traditional approach to Explainable AI (XAI) within data science heavily focuses on the "how" of explainability—utilizing mathematical methods like SHAP values, feature importance mapping, and counterfactual generation. However, a position paper from CHI '23 argues for a paradigm shift that asks *why* we are explaining these models and focuses on the human user who is attempting to learn from the explanation.

The core problem driving this shift is the sheer complexity of modern, massive, fine-tuned models. The internal logic of these systems has become so multi-dimensional that the traditional goal of providing "faithful and complete" explanations is becoming practically intractable. Humans simply cannot parse the entirety of a massive model's decision-making process in a single snapshot, necessitating explanations that are optimized for human cognition and learning theories rather than raw technical completeness.

## Counterarguments / Data Gaps

A major concern with moving away from "faithful and complete" explanations is the risk of generating "fairytale" explanations. If XAI prioritizes human comprehension over strict technical accuracy, it may inadvertently hide critical model biases, edge cases, or systemic failures behind a facade of easily digestible, but technically inaccurate, summaries. Additionally, strict regulatory and compliance standards often require mathematically rigorous proofs of decision-making that human-centered abstractions cannot satisfy.

## Related Concepts

[[SHAP Values]] [[Counterfactual Explanations]] [[Feature Importance]]

