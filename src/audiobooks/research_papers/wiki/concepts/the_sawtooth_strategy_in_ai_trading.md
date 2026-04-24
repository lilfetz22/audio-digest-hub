---
title: The Sawtooth Strategy in AI Trading
type: concept
sources:
- Author's experiment involving 3,500 prediction markets (tested up to April 2026
  models)
created: '2026-04-24'
updated: '2026-04-24'
confidence: 0.85
categories:
- Artificial Intelligence
- Game Theory
- Market Microstructure
---

## TLDR

AI agents unintentionally adopt a strategy of hoarding information early in a market and revealing it only at the end.

## Body

During simulated prediction market experiments, AI agents exhibited a fascinating, seemingly unintentional behavioral pattern termed the 'Sawtooth' strategy. In these markets, agents are tasked with trading based on private beliefs and hidden knowledge.

Instead of acting on their information immediately, the agents tended to hoard their private signals during the early rounds of trading. They only revealed their true signals and traded truthfully in the final rounds of the game. This pattern suggests the models implicitly calculated that the 'financial penalty' or strategic cost of revealing their information dropped to zero as the game concluded.

## Counterarguments / Data Gaps

It is debatable whether this behavior is a true emergent strategic capability or merely an artifact of the models' next-token prediction mechanics when processing the 'turns remaining' in a prompt. Without deeper mechanistic interpretability, it is difficult to prove the agents are actively calculating financial penalties rather than following heuristic patterns learned from their training data regarding end-of-game scenarios.

## Related Concepts

[[Logarithmic Market Scoring Rule (LMSR) in AI Markets]]

