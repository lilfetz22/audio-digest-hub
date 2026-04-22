---
title: Ordered Tokens
type: concept
sources:
- Ordered Tokens Enable Efficient Test-Time Search
created: '2026-04-22'
updated: '2026-04-22'
confidence: 0.9
categories:
- Autoregressive Models
- Tokenization
- Reasoning
---

## TLDR

A paradigm shift in tokenization that moves away from grid-based raster scans to structured sequences that facilitate reasoning and efficient test-time search.

## Body

Standard autoregressive models utilize a 2D grid-based tokenization process, akin to a raster scan, which inherently restricts the model to a greedy, sequential generation process. The 'Ordered Tokens' concept proposes that by restructuring how tokens are ordered, models can better organize information to support complex reasoning tasks.

This approach enables AI agents to leverage 'test-time search,' allowing the model to evaluate potential future states before committing to a specific output. By providing a structure that is not strictly bound by the spatial or temporal raster scan of the input, the model can effectively 'think' or deliberate before generating each subsequent token.

## Counterarguments / Data Gaps

The primary limitation of ordered tokenization is the increased complexity in mapping structured data back into a sequence that the model can process without losing critical relational information. There is also a risk that introducing non-standard ordering schemes may break compatibility with established pre-training objectives and tokenization benchmarks.

## Related Concepts

[[Test-Time Search]] [[Chain-of-Thought Prompting]] [[Autoregressive Generation]]

---

### Update (2026-04-22)

Traditional autoregressive models rely on 2D grid-based or raster-scan tokenization, which forces a strictly sequential, greedy generation process. Ordered tokens introduce a structured sequence that allows the model to prioritize critical information or reasoning steps before committing to final output generation.

This approach aims to move beyond the 'next token' limitation where models lack foresight. By imposing an order that mimics deliberate planning, the model can effectively 'think' or perform test-time search, improving the quality and logical consistency of generated outputs in complex tasks like those performed by AI agents.

**New counterarguments:** The primary limitation of ordered tokens is the potential increase in sequence length, which can exacerbate the computational cost of self-attention mechanisms in Transformers. Additionally, enforcing a specific token order may constrain the model's ability to learn diverse latent representations compared to unstructured or learnable tokenization strategies.

