# Experiment log

Protocol: hypothesis → design → control → run (fixed seeds) → official metric → decision. Negative results are logged like positive ones.

| id | date (UTC) | hypothesis | configuration | control | result | decision |
|---|---|---|---|---|---|---|
| E1 | 2026-10-28 | Successor alignment + fact diff, computed inside one Zetaris view, flags fewer assessments than section- or text-level change detection without losing most material changes | `sql/20_change_review_view.sql`, cut-off 0.60 fixed a priori; register seed 20261028; blind labels by independent annotator | A: section amended (eCFR index) · B: cited text not identical | F1 0.727 (CI 0.55–0.86) vs 0.567 / 0.594; 25 vs 48 / 45 flagged; recall 0.84 vs 1.00 | **Accepted** (lower recall than controls is the cost: 3 misses, listed) |
| E2 | 2026-10-28 | The federated SQL implements the rule exactly as specified | Independent Python re-implementation (`src/control_direct.py`) on the same sources | Python control | 48/48 identical verdicts in 3 sessions and offline in CI | **Accepted** |
| E3 | 2026-10-28 | Zetaris federation is at least as fast as direct access | 3 sessions × 30 timed runs + 3 warm-ups, same Docker network | Direct control | Zetaris median 1.79 / 2.36 / 1.85 s vs 0.46 s | **Rejected** — Zetaris is ≈1.5 s slower per run at this scale; reported as a trade-off |
| E4 | 2026-10-28 | The advantage holds without the 8 hand-picked anchor assessments | Same as E1, random sample only (n = 40) and high-confidence labels only (n = 32) | A, B | Random: 0.621 vs 0.462 / 0.490 · High-confidence: 0.800 vs 0.476 / 0.513 | **Accepted** |

Not run (would need new labels to avoid tuning on the test set): learned or tuned thresholds, synonym-aware obligation matching (`will` → `should`).
