---
title: FELA (Automated Feature Engineering)
type: concept
sources:
- FELA paper (implied context)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Machine Learning
- Feature Engineering
- Automated Machine Learning (AutoML)
- Artificial Intelligence
---

## TLDR

FELA is an automated, LLM-based feature engineering system that generates highly effective and explainable features for machine learning models.

## Body

FELA is an advanced system designed to automate the feature engineering process for machine learning pipelines. It operates by generating new, meaningful variables from raw data. Unlike traditional black-box automated machine learning (AutoML) methods, FELA is highly steerable; it explicitly outputs the "reasoning" behind every feature it creates, allowing engineers to trace the exact logic used to generate specific variables.

In practical evaluations on real-world datasets—such as gaming churn, e-commerce conversion, and fraud detection—FELA has demonstrated superior performance. It consistently outperforms state-of-the-art automated methods like OpenFE, as well as other LLM-based approaches. In one industrial fraud detection deployment, FELA successfully reduced the false-positive rate by nearly 50% compared to a baseline of features manually crafted by human experts over several weeks.

## Counterarguments / Data Gaps

While FELA outperforms existing baselines and human experts in specific deployments, the text does not detail its computational cost, latency, or the specific scale of LLM required to run it. Automated feature generation can also risk data leakage or overfitting if the evaluation pipeline is not perfectly isolated, and maintaining an LLM-in-the-loop system in real-time production environments can be prohibitively expensive.

## Related Concepts

[[Dual-Memory Architecture]] [[Structured Reasoning]] [[Decoupling Creativity from Verification]]

