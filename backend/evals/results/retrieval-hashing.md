# Retrieval evaluation

Run on 2026-10-20 · embedder `hashing-512` · chunks of 1100 chars with 160 overlap · 47 answerable questions over 4 synthetic documents (15 pages, 47 chunks).

A question counts as a hit at k if one of the top-k passages covers the page that holds the answer. MRR is the mean reciprocal rank of the first correct passage (0 if not in the top 6).

## Scoped to the question's document (how Ask works)

| Mode | hit@1 | hit@3 | hit@6 | mrr@6 | exact_hit@3 | paraphrase_hit@3 | p50_ms |
|---|---|---|---|---|---|---|---|
| dense | 0.596 | 0.809 | 0.957 | 0.728 | 0.8 | 0.812 | 0.03 |
| sparse | 0.681 | 0.872 | 0.936 | 0.787 | 1.0 | 0.812 | 0.34 |
| hybrid | 0.617 | 0.894 | 1.0 | 0.768 | 1.0 | 0.844 | 0.4 |

## Across the whole library (four documents compete)

| Mode | hit@1 | hit@3 | hit@6 | mrr@6 | exact_hit@3 | paraphrase_hit@3 | p50_ms |
|---|---|---|---|---|---|---|---|
| dense | 0.362 | 0.574 | 0.702 | 0.474 | 0.733 | 0.5 | 0.06 |
| sparse | 0.596 | 0.745 | 0.872 | 0.695 | 0.867 | 0.688 | 1.17 |
| hybrid | 0.489 | 0.723 | 0.894 | 0.632 | 0.8 | 0.688 | 1.26 |

## Ablation: how much should BM25's ranking count? (library scope)

| Fusion | hit@1 | hit@3 | hit@6 | mrr@6 |
|---|---|---|---|---|
| hybrid | 0.489 | 0.723 | 0.894 | 0.632 |
| hybrid (sparse weight 0.5) | 0.511 | 0.723 | 0.872 | 0.632 |
| hybrid (sparse weight 0.3) | 0.489 | 0.745 | 0.851 | 0.619 |

With 47 questions, one question is 0.021 of any rate, so differences this small are within noise. We keep the standard equal-weight fusion rather than tune to this set.

`exact` questions reuse a distinctive term from the document (a clause number, a figure, a name); `paraphrase` questions ask in different words.

Environment: Python 3.13.1, Windows-11. Latency is retrieval only (query embedding + scoring), not the LLM.
