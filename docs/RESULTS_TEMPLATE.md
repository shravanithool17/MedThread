# Evaluation Results Record

Use this template for an actual run of a specific checkout. Do not copy fixture values or fill fields from memory. Link the benchmark and code revision used when version control is available.

## Run metadata

| Field | Observed value |
|---|---|
| Run date/time and timezone | |
| Code revision / source snapshot | |
| Benchmark ID and version | |
| Annotation status | |
| Python and package versions | |
| Node.js/npm versions | |
| Command/API used | |

## Corpus and coverage

| Measure | Observed value |
|---|---:|
| Synthetic notes | |
| Patient/case groups | |
| Gold context annotation rows | |
| Source-aligned eligible gold examples | |
| Matched entity examples | |
| Missed entity examples | |
| Unscorable gold examples | |
| Unmatched predictions, unscorable (not FP) | |
| Excluded gold examples and reasons | |

## Entity extraction

| Metric | Value |
|---|---:|
| Recall on eligible annotated examples | |
| Precision | N/A unless exhaustive annotation supports FP counting |
| F1 | N/A unless precision is measurable and evaluation scope is valid |

Matching rule: note ID + canonical entity + punctuation-insensitive sentence tokens. Entity offsets are not currently present in gold. Do not characterize unmatched predictions as false positives under partial coverage.

## Context classification

| Sample/metric | Value |
|---|---:|
| Correctly aligned context samples | |
| Accuracy | |
| Macro precision / recall / F1 | |
| Weighted precision / recall / F1 | |

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| affirmed | | | | |
| negated | | | | |
| uncertain | | | | |
| resolved | | | | |
| unclear | | | | |

Confusion matrix: use the API fixed label order `affirmed, negated, uncertain, resolved, unclear`. Context metrics exclude missed entity predictions.

## Temporal and longitudinal tasks

| Task | Result |
|---|---|
| Temporal expression metrics | Not available until gold temporal labels are annotated |
| Longitudinal decision metrics | Not available until gold longitudinal cases are annotated |
| Patient-group holdout | None in current benchmark |

## Error analysis and limitations

Attach source-linked error examples from the Evaluation API/UI. Include expected and predicted label, note ID, sentence, category, and alignment status. State the partial annotation coverage, independent review status, synthetic provenance, absence of held-out test data, and lack of clinical validity. Do not report synthetic results as clinical performance.
