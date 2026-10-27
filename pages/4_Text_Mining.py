"""Text Mining — corpus-level statistics and frequency analysis."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import pandas as pd

from medthread.text_mining import (
    entity_frequency,
    context_distribution,
    status_distribution,
    compute_corpus_stats,
)
from medthread.styles import (
    THEME_CSS, escape, badge, stat_tile, CONTEXT_COLORS, CONTEXT_PALETTE,
    STATUS_COLORS, PLOTLY_LAYOUT,
    CYAN, TEAL, AMBER, CORAL, BLUE, EMERALD, BORDER, BG_CARD, T1, T2,
)

st.set_page_config(page_title="Text Mining — MedThread", page_icon="📊", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)

for key, default in [
    ("notes", []), ("mentions_df", pd.DataFrame()),
    ("comparison_df", pd.DataFrame()), ("pipeline_run", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding-bottom:1rem;border-bottom:1px solid {BORDER};margin-bottom:1.25rem">
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">📊 Text Mining</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    Corpus-level statistics for the loaded dataset ·
    <span style="color:#f59e0b">Counts describe text mentions only — not disease prevalence or patient risk</span>
  </p>
</div>
""", unsafe_allow_html=True)

mentions_df = st.session_state.mentions_df
comparison_df = st.session_state.comparison_df

if not st.session_state.pipeline_run:
    st.info("No data loaded. Load demo data or upload notes from the Home page.")
    st.stop()

# ── Summary stat tiles ────────────────────────────────────────────────────────
stats = compute_corpus_stats(mentions_df, comparison_df, st.session_state.notes)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_tile(stats["n_patients"], "Patients", CYAN), unsafe_allow_html=True)
with c2:
    st.markdown(stat_tile(stats["n_notes"], "Notes", TEAL), unsafe_allow_html=True)
with c3:
    st.markdown(stat_tile(stats["n_mentions"], "Mentions", BLUE), unsafe_allow_html=True)
with c4:
    st.markdown(stat_tile(stats["n_review_flags"], "Review Flags", AMBER), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if mentions_df.empty:
    st.info("No entity mentions were extracted from the loaded notes.")
    st.stop()

# ── Charts row ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

freq_df = entity_frequency(mentions_df)
ctx_df = context_distribution(mentions_df)

with col1:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Symptom Mention Frequency</div>', unsafe_allow_html=True)
    st.caption("Count of extracted mentions per entity in the loaded corpus.")
    try:
        import plotly.express as px
        fig = px.bar(
            freq_df, x="entity_normalized", y="count",
            color="count",
            color_continuous_scale=[[0, "#14b8a6"], [0.5, "#22d3ee"], [1, "#60a5fa"]],
            labels={"entity_normalized": "", "count": "Mentions"},
            height=340,
        )
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, xaxis_tickangle=-35, coloraxis_showscale=False)
        fig.update_traces(marker_line_color="#080c18", marker_line_width=1)
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.dataframe(freq_df, hide_index=True, use_container_width=True)

with col2:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Context Label Distribution</div>', unsafe_allow_html=True)
    st.caption("How the NLP pipeline classifies each mention.")
    try:
        import plotly.express as px
        fig = px.pie(
            ctx_df, names="context", values="count",
            color="context",
            color_discrete_map=CONTEXT_PALETTE,
            hole=0.45,
            height=340,
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            showlegend=True,
            legend=dict(
                bgcolor="rgba(20,30,53,0.9)",
                bordercolor=BORDER,
                borderwidth=1,
                font=dict(color=T2, size=11),
            ),
        )
        fig.update_traces(textposition="outside", textfont_size=11,
                          marker=dict(line=dict(color="#080c18", width=2)))
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.dataframe(ctx_df, hide_index=True, use_container_width=True)

# ── Status distribution ────────────────────────────────────────────────────────
st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Cross-Visit Status Distribution</div>', unsafe_allow_html=True)
st.caption("Longitudinal comparison status per (patient, entity) pair.")

status_df = status_distribution(comparison_df)
try:
    import plotly.express as px
    status_palette = {s: c for s, (c, _) in STATUS_COLORS.items()}
    fig = px.bar(
        status_df, x="status", y="count",
        color="status",
        color_discrete_map=status_palette,
        height=300,
        labels={"status": "", "count": "Count"},
    )
    fig.update_layout(**PLOTLY_LAYOUT, showlegend=False, xaxis_tickangle=-15)
    fig.update_traces(marker_line_color="#080c18", marker_line_width=1)
    st.plotly_chart(fig, use_container_width=True)
except ImportError:
    st.dataframe(status_df, hide_index=True, use_container_width=True)

# ── Full mentions table ────────────────────────────────────────────────────────
st.divider()
st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">All Extracted Mentions</div>', unsafe_allow_html=True)
st.caption("Every mention extracted from the loaded corpus with evidence sentences.")

col1, col2, col3 = st.columns(3)
with col1:
    entity_filter = st.selectbox(
        "Entity", ["All"] + sorted(mentions_df["entity_normalized"].unique()),
    )
with col2:
    context_filter = st.selectbox(
        "Context", ["All"] + sorted(mentions_df["context"].unique()),
    )
with col3:
    patient_filter = st.selectbox(
        "Patient", ["All"] + sorted(mentions_df["patient_id"].unique()),
    )

filtered = mentions_df.copy()
if entity_filter != "All":
    filtered = filtered[filtered["entity_normalized"] == entity_filter]
if context_filter != "All":
    filtered = filtered[filtered["context"] == context_filter]
if patient_filter != "All":
    filtered = filtered[filtered["patient_id"] == patient_filter]

st.markdown(
    f'<p style="font-size:0.82rem;color:{T2}">Showing <strong style="color:#e2e8f0">{len(filtered)}</strong> of {len(mentions_df)} mentions</p>',
    unsafe_allow_html=True,
)

display_cols = [
    "patient_id", "note_id", "visit_date", "entity_normalized",
    "context", "sentence", "reason", "time_expression",
]
available = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available], use_container_width=True, hide_index=True)
