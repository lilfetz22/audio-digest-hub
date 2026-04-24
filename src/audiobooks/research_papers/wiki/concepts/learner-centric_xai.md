---
title: Learner-Centric XAI
type: concept
sources: []
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Explainable AI (XAI)
- Human-Computer Interaction (HCI)
- Cognitive Science
---

## TLDR

A conceptual framework in Explainable AI that prioritizes a user's long-term skill acquisition and task performance over providing a complete technical trace of the model.

## Body

Learner-Centric XAI represents a paradigm shift from traditional 'Model-Centric XAI'. Instead of focusing on exposing every weight, node, or feature importance score, this approach emphasizes the utility of the explanation for the end-user. For example, in clinical settings, explanations should scaffold the clinician's decision-making process rather than overwhelming them with technical model dumps.

Furthermore, this framework suggests that the ultimate goal of an explanation is not necessarily to trace an algorithm, but to provide well-timed interventions. These interventions are designed to help the human operator build a more accurate mental model of the AI system's limitations, thereby optimizing for long-term skill acquisition rather than just immediate clarity.

## Counterarguments / Data Gaps

Evaluating learner-centric systems requires complex, longitudinal studies to measure actual skill acquisition, which is much harder to quantify than standard metrics like explanation fidelity. Additionally, designing these tailored, context-aware interventions requires significant domain expertise and HCI resources compared to using off-the-shelf XAI techniques like SHAP or LIME.

## Related Concepts

[[Model-Centric XAI]] [[Interactive Probing]] [[Formative Evaluation]]

