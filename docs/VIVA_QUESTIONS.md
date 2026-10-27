# MedThread Viva Questions and Answers

1. **What problem does MedThread address?**  
   It demonstrates extraction and evidence-based review of symptom mentions across synthetic longitudinal notes.

2. **Is MedThread a clinical decision-support or diagnostic product?**  
   No. It is an educational prototype; its outputs are unvalidated text-processing signals and require expert review.

3. **What is the application architecture?**  
   React/Vite/TypeScript frontend, FastAPI REST backend, and reusable Python modules under `src/medthread/`.

4. **What is the pipeline order?**  
   Validation and sentence splitting, lexicon extraction, context classification, temporal phrase processing, then patient-grouped longitudinal rules.

5. **How are entities extracted?**  
   Configured aliases are matched with word-boundary regex, or optional spaCy PhraseMatcher; overlapping spans are filtered longest-first.

6. **How is a negated concept handled?**  
   Clause-scoped cue rules assign `negated`; cue scope is heuristic and can fail on complex syntax.

7. **Does “improved” mean resolved?**  
   No. Partial improvement alone is not explicit resolution. Resolution requires explicit resolution language.

8. **Does a missing mention mean the symptom is absent?**  
   No. Missing documentation is not the same as negation or resolution.

9. **What is “newly documented”?**  
   It describes first appearance in the available record, not biological onset.

10. **How are temporal phrases normalized?**  
    A limited set of regular-expression patterns is normalized relative to the note date when possible; ambiguous phrases remain unnormalized.

11. **How does the system avoid comparing different patients?**  
    Longitudinal groups include patient ID and normalized entity, so different patient groups are analyzed separately.

12. **What does a possible inconsistency mean?**  
    It is a rule-generated review flag for potentially conflicting documented contexts, not a confirmed contradiction.

13. **What does same-note co-occurrence mean?**  
    Only that the extractor found both concepts in one source note. It does not imply causation, diagnosis, prevalence, or clinical relationship.

14. **What is the evaluation benchmark?**  
    A small project-authored context-example CSV over 15 synthetic notes and five patient groups.

15. **Has the benchmark been independently adjudicated?**  
    No independent review is documented; it is marked author-annotated and not independently reviewed.

16. **Why are extraction precision and F1 unavailable?**  
    Entity annotations are partial, so unmatched predictions cannot validly be counted as false positives. Recall on eligible annotated examples can be reported separately.

17. **How are context metrics aligned?**  
    By note ID, canonical entity, and punctuation-insensitive source sentence tokens. Only correctly aligned mentions contribute to context metrics.

18. **How are missing gold mentions handled?**  
    They are reported as missed extraction examples, excluded from context-classification scores.

19. **Why are there no temporal or longitudinal metrics?**  
    The current gold data does not contain temporal or longitudinal labels.

20. **Is there a train/test split?**  
    No. The current system fits no ML model. Its scores are development checks on the bundled corpus, not held-out estimates.

21. **What would be needed for a valid extraction precision estimate?**  
    An explicitly scoped, exhaustive annotation of entity spans including all target and non-target cases, with independent review and coverage metadata.

22. **What is the next credible evaluation step?**  
    Build and adjudicate an exhaustive synthetic benchmark with span offsets, negative examples, temporal/longitudinal labels, then split by patient/case before any model training or tuning.

23. **Why not add an ML classifier now?**  
    The current benchmark is small, partial, and not split by patient; fitting a model would make evaluation unreliable and risk leakage.

24. **What are the main limitations?**  
    Small synthetic data, incomplete/unreviewed annotations, lexicon coverage, heuristic context scope and time parsing, no held-out split, and no clinical validation.

25. **How can the demonstration be reproduced?**  
    Follow setup and run commands in the root README and version/environment notes in `REPRODUCIBILITY.md`.

26. **What persists after restarting the FastAPI backend?**
    The active source notes, dataset metadata, latest reviewer decisions, optional rationale, timestamps, and review-event history persist in local SQLite. NLP results are recomputed from source notes at startup. Replacing/resetting the dataset clears review decisions.

27. **Does local persistence make MedThread safe for real patient data?**
    No. SQLite stores note text in plaintext and the prototype has no encryption or clinical security controls. Use only synthetic or otherwise appropriately de-identified data.

28. **How are source mention highlights kept aligned with original text?**
    The API validates zero-based, half-open Unicode code-point offsets against the original note. React converts them to UTF-16 indices before slicing; invalid offsets are not exposed as valid source links.
