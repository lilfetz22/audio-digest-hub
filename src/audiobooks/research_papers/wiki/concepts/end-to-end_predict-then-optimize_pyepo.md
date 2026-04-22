---
title: End-to-End Predict-then-Optimize (PyEPO)
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Machine Learning
- Operations Research
- Decision Theory
---

## TLDR

A framework that integrates machine learning prediction with optimization tasks to minimize decision regret rather than prediction error.

## Body

The PyEPO framework moves away from the traditional 'two-stage' approach, where a machine learning model is trained to predict parameters and an optimization solver is then applied to those predictions. Instead, it embeds the optimization process directly into the training loop of the machine learning model. By doing so, the model learns to prioritize accuracy on features that directly impact the optimal decision outcome, rather than optimizing for a generic statistical metric like Mean Squared Error (MSE).

This paradigm shift is particularly effective in high-stakes environments like logistics or resource allocation. By focusing on decision regret, the model can afford to be less accurate on parameters that have little influence on the final decision, while focusing its predictive power on variables that drive significant cost or efficiency differences.

## Counterarguments / Data Gaps

The primary limitation is the increased complexity of calculating gradients through optimization layers, which can be computationally expensive. Additionally, if the downstream optimization problem is poorly formulated or the training data is highly noisy, the model may converge to sub-optimal decision policies that are difficult to debug compared to simple regression models.

## Related Concepts

[[Predict-then-Optimize]] [[Decision-Focused Learning]] [[Regret Minimization]]

