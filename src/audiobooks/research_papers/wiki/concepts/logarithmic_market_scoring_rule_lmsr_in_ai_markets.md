---
title: Logarithmic Market Scoring Rule (LMSR) in AI Markets
type: concept
sources:
- Author's experiment involving 3,500 prediction markets (tested up to April 2026
  models)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.95
categories:
- Economics
- Artificial Intelligence
- Mathematics
---

## TLDR

A mathematical mechanism used in AI prediction markets that forces prices to respond linearly to the log-odds of agents' private beliefs.

## Body

The Logarithmic Market Scoring Rule (LMSR) is a well-established mathematical mechanism used in prediction markets, which has been adapted to test the reasoning capabilities of Large Language Models (LLMs). In this experimental setup, LLMs act as trading agents tasked with inferring hidden knowledge.

The LMSR functions by forcing the market price to respond linearly to the log-odds of the agents' private beliefs. By utilizing this rule, researchers can quantitatively measure the agents' success and reasoning abilities through 'log error'—a metric that calculates how far the final market price deviates from the actual ground truth of the environment.

## Counterarguments / Data Gaps

While LMSR is mathematically sound for human and theoretical markets, LLMs are not inherently designed to output calibrated probabilities natively without specific prompting or fine-tuning. Therefore, a high 'log error' might measure the model's poor prompt-following or probability calibration abilities rather than its fundamental capacity to infer hidden knowledge.

## Related Concepts

[[Complexity Penalty in AI Reasoning]] [[The Sawtooth Strategy in AI Trading]]

