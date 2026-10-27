"""Evaluation — precision/recall/F1 against gold annotations."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import pandas as pd

from medthread.evaluation import (
    load_gold_annotations,
    align_predictions_with_gold,
    compute_context_metrics,
    find_errors,
)
from medthread.pipeline import run_pipeline
from medthread.validation import load_notes_from_csv
from medthread.styles import (
    THEME_CSS, escape, badge, stat_tile, CONTEXT_COLORS, CONTEXT_PALETTE,
    PLOTLY_LAYOUT, CYAN, TEAL, AMBER, CORAL, BLUE, EMERALD, BORDER, BG_CARD, T1, T2,
)

st.set_page_config(page_title="Evaluation — MedThread", page_icon="📐", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)

for key, default in [
    ("notes", []), ("mentions_df", pd.DataFrame()),
    ("comparison_df", pd.DataFrame()), ("pipeline_run", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

GOLD_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'gold_annotations.csv')
SYNTHETIC_NOTES_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'synthetic_notes.csv')

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding-bottom:1rem;border-bottom:1px solid {BORDER};margin-bottom:1.25rem">
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">📐 Evaluation Lab</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    Precision, recall, and F1 computed against explicit human-authored gold annotations
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:rgba(245,158,11,0.07);border:1px solid rgba(245,158,11,0.2);
            border-radius:8px;padding:0.75rem 1rem;font-size:0.82rem;color:{T2};margin-bottom:1.25rem">
  ⚠ <strong style="color:{AMBER}">Important:</strong>
  Gold annotations were authored explicitly by the project team — not generated from model predictions.
  Metrics reflect performance on a small synthetic benchmark only.
  Results <strong style="color:#e2e8f0">cannot be generalised</strong> to real clinical text.
</div>
""", unsafe_allow_html=True)


def render_evaluation(gold_df: pd.DataFrame, pred_mentions: list) -> None:
    """Run and display full evaluation results."""
    aligned = align_predictions_with_gold(gold_df, pred_mentions)
    result = compute_context_metrics(aligned)

    n_samples = result["overall"].get("n_samples", 0)
    accuracy = result["overall"].get("accuracy", "N/A")
    macro_f1 = result["overall"].get("macro_f1", "N/A")
    weighted_f1 = result["overall"].get("weighted_f1", "N/A")

    # ── Overall metrics ──
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Overall Metrics</div>', unsafe_allow_html=True)
    st.caption(f"Sample size: {n_samples} aligned annotation pairs")

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(stat_tile(accuracy, "Accuracy", EMERALD), unsafe_allow_html=True)
    with mc2:
        st.markdown(stat_tile(macro_f1, "Macro F1", CYAN), unsafe_allow_html=True)
    with mc3:
        st.markdown(stat_tile(weighted_f1, "Weighted F1", TEAL), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-class metrics ──
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Per-Class Metrics</div>', unsafe_allow_html=True)
    per_class = result.get("per_class", pd.DataFrame())
    if not per_class.empty:
        # Render with context badges in context column
        if "context" in per_class.columns:
            rows_html = ""
            for _, row in per_class.iterrows():
                ctx = str(row.get("context", ""))
                ctx_badge = badge(ctx, CONTEXT_COLORS) if ctx else ""

                def fmt_val(v):
                    try:
                        return f"{float(v):.3f}"
                    except Exception:
                        return escape(str(v))

                prec = fmt_val(row.get("precision", ""))
                rec  = fmt_val(row.get("recall", ""))
                f1   = fmt_val(row.get("f1_score", row.get("f1-score", "")))
                sup  = escape(str(row.get("support", "")))

                rows_html += (
                    f'<tr style="border-bottom:1px solid {BORDER}">'
                    f'<td style="padding:0.4rem 0.5rem">{ctx_badge}</td>'
                    f'<td style="padding:0.4rem 0.5rem;text-align:right;font-size:0.85rem">{prec}</td>'
                    f'<td style="padding:0.4rem 0.5rem;text-align:right;font-size:0.85rem">{rec}</td>'
                    f'<td style="padding:0.4rem 0.5rem;text-align:right;font-size:0.85rem;color:{CYAN};font-weight:700">{f1}</td>'
                    f'<td style="padding:0.4rem 0.5rem;text-align:right;font-size:0.82rem;color:#64748b">{sup}</td>'
                    f'</tr>'
                )
            st.markdown(
                f'<table style="width:100%;border-collapse:collapse">'
                f'<thead><tr style="border-bottom:1px solid {BORDER}">'
                f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Context</th>'
                f'<th style="padding:0.35rem 0.5rem;text-align:right;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Precision</th>'
                f'<th style="padding:0.35rem 0.5rem;text-align:right;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Recall</th>'
                f'<th style="padding:0.35rem 0.5rem;text-align:right;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">F1</th>'
                f'<th style="padding:0.35rem 0.5rem;text-align:right;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Support</th>'
                f'</tr></thead><tbody>{rows_html}</tbody></table>',
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(per_class, use_container_width=True, hide_index=True)
    else:
        st.warning("No per-class metrics available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Confusion matrix ──
    cm = result.get("confusion_matrix")
    if cm is not None and hasattr(cm, "shape"):
        st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Confusion Matrix</div>', unsafe_allow_html=True)
        st.caption("Rows = gold label · Columns = predicted label · diagonal = correct predictions")
        try:
            import plotly.express as px
            fig = px.imshow(
                cm, text_auto=True,
                color_continuous_scale=[[0, "#141e35"], [0.5, "#164e63"], [1, "#22d3ee"]],
                labels=dict(x="Predicted", y="Gold", color="Count"),
                height=360,
            )
            fig.update_layout(
                **PLOTLY_LAYOUT,
                coloraxis_showscale=False,
                xaxis_title="Predicted",
                yaxis_title="Gold",
            )
            fig.update_traces(textfont=dict(color="#e2e8f0"))
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.dataframe(pd.DataFrame(cm), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Error analysis ──
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Error Analysis</div>', unsafe_allow_html=True)
    errors = find_errors(aligned)
    if not errors.empty:
        st.caption(f"{len(errors)} mismatches (false positives / false negatives)")
        st.dataframe(errors, use_container_width=True, hide_index=True)
    else:
        st.success("No mismatches found in the evaluation set.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Aligned predictions vs gold ──
    with st.expander("Aligned Predictions vs Gold Annotations (full table)"):
        st.dataframe(aligned, use_container_width=True, hide_index=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊  Bundled Data (Synthetic)", "📁  Custom Gold Annotations"])

with tab1:
    st.markdown(
        f'<p style="color:{T2};font-size:0.88rem">Evaluates the pipeline against the bundled gold annotations on the included synthetic dataset.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="font-size:0.82rem;color:#64748b">Gold file: <code style="color:{CYAN}">data/gold_annotations.csv</code></p>',
        unsafe_allow_html=True,
    )

    if st.button("▶  Run Evaluation on Bundled Data", type="primary"):
        with st.spinner("Loading gold annotations and running pipeline…"):
            gold_df, gold_errors = load_gold_annotations(GOLD_PATH)
            for e in gold_errors:
                st.warning(e)

            with open(SYNTHETIC_NOTES_PATH, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            notes, _ = load_notes_from_csv(csv_content)
            mentions_df, _ = run_pipeline(notes)

        if gold_df.empty:
            st.error("Could not load gold annotations.")
        elif mentions_df.empty:
            st.error("Pipeline produced no mentions.")
        else:
            render_evaluation(gold_df, mentions_df.to_dict("records"))
            st.info(
                "These metrics are on a small synthetic benchmark (≈60 gold instances). "
                "They do not validate clinical accuracy or generalise to real clinical text."
            )

with tab2:
    st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;
            padding:1rem 1.25rem;margin-bottom:1rem;font-size:0.84rem;color:{T2}">
  Upload your own gold annotation CSV.<br><br>
  <strong style="color:#e2e8f0">Required columns:</strong>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">note_id</code>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">sentence</code>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">entity_normalized</code>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">context</code><br>
  <span style="font-size:0.8rem">context must be one of:
    affirmed · negated · uncertain · resolved · unclear</span>
</div>
""", unsafe_allow_html=True)

    uploaded_gold  = st.file_uploader("Gold annotation CSV", type=["csv"], key="gold_upload")
    uploaded_notes = st.file_uploader("Corresponding notes CSV", type=["csv"], key="eval_notes_upload")

    if uploaded_gold and uploaded_notes:
        if st.button("▶  Run Custom Evaluation", type="primary"):
            with st.spinner("Running…"):
                gold_df, gold_errors = load_gold_annotations(uploaded_gold.read())
                for e in gold_errors:
                    st.warning(e)

                notes, note_errors = load_notes_from_csv(uploaded_notes.read())
                for e in note_errors:
                    st.warning(e)

                mentions_df, _ = run_pipeline(notes)

            if not gold_df.empty and not mentions_df.empty:
                render_evaluation(gold_df, mentions_df.to_dict("records"))
            elif gold_df.empty:
                st.error("Gold annotations could not be loaded.")
            else:
                st.error("Pipeline produced no mentions from the provided notes.")
