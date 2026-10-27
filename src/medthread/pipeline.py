"""Main pipeline orchestrator.

Runs the full NLP pipeline on a list of Notes and returns annotated mentions
and comparison results.
"""

from __future__ import annotations

from .schemas import Note, Mention, ComparisonResult
from .entity_extraction import extract_mentions_from_notes
from .context_detection import annotate_mentions_with_context
from .temporal import annotate_mentions_with_temporal
from .longitudinal_analysis import run_longitudinal_analysis
from .text_mining import mentions_to_dataframe, comparison_results_to_dataframe

import pandas as pd


def run_pipeline(notes: list[Note]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Full pipeline: notes → annotated mentions → comparison results.
    Returns (mentions_df, comparison_df).
    """
    if not notes:
        return (
            mentions_to_dataframe([]),
            comparison_results_to_dataframe([]),
        )

    # Step 1: Extract raw mentions
    raw_mentions = extract_mentions_from_notes(notes)

    # Step 2: Annotate with context (negation, uncertainty, resolution)
    context_mentions = annotate_mentions_with_context(raw_mentions)

    # Step 3: Annotate with temporal expressions
    full_mentions = annotate_mentions_with_temporal(context_mentions)

    # Step 4: Longitudinal comparison
    comparison_results = run_longitudinal_analysis(full_mentions)

    mentions_df = mentions_to_dataframe(full_mentions)
    comparison_df = comparison_results_to_dataframe(comparison_results)

    return mentions_df, comparison_df
