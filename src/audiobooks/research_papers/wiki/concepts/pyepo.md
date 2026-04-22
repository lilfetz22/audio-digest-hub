---
title: PyEPO
type: concept
sources:
- 'PyEPO: A PyTorch-based End-to-End Predict-then-Optimize Library for Linear and
  Integer Programming'
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.95
categories:
- Software Engineering
- Machine Learning Frameworks
- Mathematical Programming
---

## TLDR

A PyTorch-based software library designed to facilitate end-to-end learning by integrating linear and integer programming solvers into deep learning workflows.

## Body

PyEPO is an open-source library that serves as an interface between standard deep learning frameworks, specifically PyTorch, and classical optimization solvers. It provides the necessary infrastructure to incorporate optimization problems as layers within neural network architectures. 

By providing standardized tools for implementing PtO pipelines, PyEPO enables developers to define complex objective functions and constraints, automatically handling the integration with modern gradient-based optimizers. It simplifies the transition from theoretical research in decision-focused learning to practical deployment in logistics, scheduling, and grid management.

## Counterarguments / Data Gaps

As a library, PyEPO is dependent on the performance and scope of the underlying solvers it wraps; it may not support all types of non-convex or highly non-linear optimization constraints. Additionally, performance bottlenecks may occur when scaling to extremely high-dimensional optimization problems with millions of decision variables.

## Related Concepts

[[PyTorch]] [[Linear Programming]] [[Integer Programming]]

---

### Update (2026-04-22)

PyEPO functions as a bridge between machine learning pipelines and classical optimization solvers. By wrapping solvers like Gurobi or Pyomo, it allows the optimization process to be treated as a differentiable layer within a neural network. This enables backpropagation through the optimization task, allowing models to learn parameters that directly improve the objective of the downstream optimization problem.

Traditionally, optimization solvers act as black-box components that provide solutions based on inputs. PyEPO transforms this relationship, allowing the AI to 'act' through optimization. By integrating the solver into the architecture, the machine learning model can learn to make predictions specifically optimized for the constraints and goals of the target combinatorial problem.

**New counterarguments:** Differentiating through optimization solvers can be computationally expensive, particularly for large-scale combinatorial problems where the sensitivity analysis (gradient calculation) requires solving multiple sub-problems. Additionally, not all optimization problems have continuous objective functions or constraints, which can lead to vanishing or ill-defined gradients during training.

