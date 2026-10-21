# Retrieval evaluation

Run on 2026-10-21 · embedder `BAAI/bge-small-en-v1.5` · chunks of 1100 chars with 160 overlap · 47 answerable questions over 4 synthetic documents (15 pages, 47 chunks).

**Caveat:** the documents and questions were written by the same person who built the retrieval pipeline, and the corpus is small (a document-scoped search picks from about a dozen passages). Treat this as a regression suite and a comparison between modes, not as accuracy on real-world documents.

A question counts as a hit at k if one of the top-k passages covers the page that holds the answer. MRR is the mean reciprocal rank of the first correct passage (0 if not in the top 6).

## Scoped to the question's document (how Ask works)

| Mode | hit@1 | hit@3 | hit@6 | mrr@6 | exact_hit@3 | paraphrase_hit@3 | p50_ms |
|---|---|---|---|---|---|---|---|
| dense | 0.83 | 0.957 | 0.979 | 0.892 | 1.0 | 0.938 | 6.47 |
| sparse | 0.681 | 0.872 | 0.936 | 0.787 | 1.0 | 0.812 | 0.49 |
| hybrid | 0.787 | 0.915 | 1.0 | 0.866 | 1.0 | 0.875 | 6.48 |

## Across the whole library (four documents compete)

| Mode | hit@1 | hit@3 | hit@6 | mrr@6 | exact_hit@3 | paraphrase_hit@3 | p50_ms |
|---|---|---|---|---|---|---|---|
| dense | 0.809 | 0.936 | 0.979 | 0.871 | 1.0 | 0.906 | 6.21 |
| sparse | 0.596 | 0.745 | 0.872 | 0.695 | 0.867 | 0.688 | 1.38 |
| hybrid | 0.745 | 0.894 | 0.957 | 0.83 | 1.0 | 0.844 | 7.59 |

## Ablation: how much should BM25's ranking count? (library scope)

| Fusion | hit@1 | hit@3 | hit@6 | mrr@6 |
|---|---|---|---|---|
| hybrid | 0.745 | 0.894 | 0.957 | 0.83 |
| hybrid (sparse weight 0.5) | 0.745 | 0.915 | 0.979 | 0.841 |
| hybrid (sparse weight 0.3) | 0.745 | 0.957 | 0.979 | 0.845 |

With 47 questions, one question is 0.021 of any rate, so differences this small are within noise. We keep the standard equal-weight fusion rather than tune to this set.

`exact` questions reuse a distinctive term from the document (a clause number, a figure, a name); `paraphrase` questions ask in different words.

Environment: Python 3.13.1, Windows-11. Latency is retrieval only (query embedding + scoring), not the LLM.
