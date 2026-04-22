---
title: Predict-then-Optimize (PtO)
type: concept
sources:
- Recent research in decision-focused learning and integrated PtO frameworks
- 'PyEPO: A PyTorch-based End-to-End Predict-then-Optimize Library for Linear and
  Integer Programming'
- https://github.com/PyEPO-dev/PyEPO
created: '2026-04-22'
updated: '2026-04-22'
confidence: 1.0
categories:
- Machine Learning
- Mathematical Optimization
- Decision Science
---

## TLDR

A paradigm that integrates machine learning for parameter estimation with mathematical optimization to minimize decision loss rather than prediction error.

## Body

The Predict-then-Optimize (PtO) framework addresses decision-making tasks where the objective function coefficients are unknown and must be estimated from data. Traditional pipelines often decompose this into a sequential two-stage process: first, an ML model predicts the coefficients, and second, an optimization solver uses these predictions to determine an optimal decision. 

In the PtO paradigm, the optimization solver is embedded directly into the machine learning training loop. This allows the model to be trained using a loss function that reflects the quality of the final decision (the 'decision loss') rather than the proximity of the predicted coefficients to their true values. By doing so, the model learns to prioritize accuracy on parameters that significantly impact the optimization objective, effectively bridging the gap between predictive performance and prescriptive utility. 

[NEW ADDITION] Furthermore, the paradigm acknowledges that decoupled strategies often fail because traditional ML models are agnostic to the downstream optimization process. By incorporating decision quality into the training objective, the model learns to prioritize accuracy on parameters that significantly impact the final decision, rather than minimizing global prediction error.

## Counterarguments / Data Gaps

The primary limitation is the computational complexity of differentiating through the optimization layer, which often requires calculating gradients of discrete or non-smooth combinatorial problems. Furthermore, the surrogate loss functions used in these loops may not always perfectly align with the actual decision regret, potentially leading to instability during training. [NEW ADDITION] Additionally, embedding solvers into the training loop significantly increases the computational overhead, potentially making training prohibitively slow for large-scale problems.

## Related Concepts

[[Linear Programming]] [[Integer Programming]] [[End-to-End Learning]]

