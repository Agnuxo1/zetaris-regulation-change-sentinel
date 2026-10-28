# Modal-aware v2: one more material change recovered

The v1 fact extractor records obligation words such as `must`, `may` and
`should`. It can miss a change when the text already contains `should` in
another sentence: replacing `will` by `should` then leaves that token set
unchanged. The v2 candidate also tracks whole-word `will` and `can`.

The aligner, section boundaries, edit-distance threshold, numeric extraction
and original controls are unchanged. The Python reference accepts a fact
extractor argument; the new implementation and the SQL view use the same
extra vocabulary. Version 1 remains available for exact reproduction.

| Same 48 labelled assessments | v1 | modal v2 |
|---|---:|---:|
| True material changes found | 16 / 19 | **17 / 19** |
| False positives | 9 | **9** |
| Recall | 0.8421 | **0.8947** |
| Precision | 0.6400 | **0.6538** |
| F1 | 0.7273 | **0.7556** |
| Assessments queued for review | 25 | 26 |

Only **NCHA-037** changes verdict, from `EDITORIAL_ONLY` to
`REVIEW_MATERIAL`. The benefit is one recovered material change for one
additional review, with no additional false alarm in this benchmark.

This is an **exploratory improvement after inspecting known errors**. The
paired section-cluster bootstrap interval for ΔF1 is [0, 0.1068], 2,000
resamples, seed 20261028. These 48 assessments are not a new blind validation
set. New independently labelled sections are needed to estimate generalisation.
The eCFR passages are real; the organisation's register is fictional.

All three interventions were retained, including the two that did not improve F1:

| Intervention | F1 | Recall | False positives | Decision |
|---|---:|---:|---:|---|
| Add `will` / `can` | **0.7556** | **0.8947** | 9 | Implement as versioned v2 candidate |
| Add approver-role differences | 0.7234 | 0.8947 | 11 | Keep as experiment; do not combine automatically |
| Tighten alignment cutoff to 0.45 | 0.7111 | 0.8421 | 10 | Keep the original 0.60 cutoff |

The live federated view has been provisioned and queried after restoring the
stopped services. Its 48 verdicts match the independently executed Python rule
exactly: see `results/modal-v2/live-agreement.json`. The first post-restart
query took 12.597 s wall time; this cold run is not a controlled speed comparison.

Reproduce the Python candidate without credentials:

```sh
python -m src.control_modal_v2
pytest -q
```

Provision and use the corresponding live view with existing Zetaris credentials:

```sh
python -m src.sentinel provision --variant modal-v2
python -m src.sentinel review --variant modal-v2
```

The live candidate writes to `results/modal-v2-live/`; the original video,
`results/latest/`, labels, v1 SQL and historical experiment results stay separate.
The video demonstrates v1; it is not presented as a capture of v2. Offline
numbers and live SQL/Python agreement have separate evidence files.
