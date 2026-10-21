# Answer evaluation

Run on 2026-10-21 with `gemini-3.5-flash-lite` over 54 questions.

| Metric | Value |
|---|---|
| accuracy | 0.979 |
| correct refusals | 0.857 |
| false refusals | 0.0 |
| grounded claims | 1.0 |
| stated unverified claims | 0 |
| latency p50 ms | 1890 |
| latency p95 ms | 14526 |
| mean tokens | 1014 |

Misses:

- `msa-13` (partial): The first contract period is at least twelve months, as indicated by the mention of the first twelve months before which termination for convenience is not allowed.
- `min-08` (partial): Neha Kulkarni holds the role of Sales and gave apologies for the meeting.
