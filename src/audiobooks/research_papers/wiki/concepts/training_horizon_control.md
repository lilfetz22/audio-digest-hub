---
title: Training Horizon Control
type: concept
sources: []
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.92
categories:
- Continual Learning
- Training Heuristics
---

## TLDR

Careful management of the training horizon via early stopping is a more effective lever for mitigating forgetting than many complex architectural regularizers.

## Body

The training horizon, defined as the total number of gradient descent steps performed on a task, is a critical variable in model stability. The paper identifies a 'forgetting zone' that the model enters if it is over-trained on a subsequent task, implying that excessive optimization on new data leads to the rapid degradation of previous task performance.

The authors suggest that targeted early stopping is a highly effective, low-complexity method to combat this. By limiting the number of updates, the model remains within a stable manifold, preventing the 'bleeding' of parameters that results in catastrophic forgetting. This approach is positioned as a superior alternative to complex architectural modifications, offering a precise lever to balance performance on new tasks against the retention of historical ones.

## Counterarguments / Data Gaps

The primary limitation of relying on early stopping is the trade-off with peak performance on the current task. Stopping early might prevent the model from reaching the global or a sufficient local minimum for the task at hand, potentially resulting in sub-optimal task accuracy even if it successfully preserves historical memory.

## Related Concepts

[[Early Stopping]] [[Gradient Descent]] [[Continual Learning]]

