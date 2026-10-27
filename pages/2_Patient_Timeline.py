"""Patient Timeline — per-patient symptom timeline and evidence."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import pandas as pd

from medthread.text_mining import build_patient_timeline
from medthread.styles import (
    THEME_CSS, escape, badge, CONTEXT_COLORS, CONTEXT_PALETTE, PLOTLY_LAYOUT,
    CYAN, TEAL, BORDER, T1, T2, BG_CARD,
)

st.set_page_config(page_title="Patient Timeline — MedThread", page_icon="📅", layout="wide")
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
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">📅 Patient Timeline</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    Track symptom mentions across visits for each patient
  </p>
</div>
""", unsafe_allow_html=True)

mentions_df = st.session_state.mentions_df

if not st.session_state.pipeline_run or mentions_df.empty:
    st.info("No data loaded. Load demo data or upload notes from the Home or Clinical Notes pages.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 3])

patient_ids = sorted(mentions_df["patient_id"].unique())
with col1:
    # Default to first patient so chart isn't overwhelming
    default_idx = 1  # index 1 = first real patient (index 0 = "All")
    selected_pid = st.selectbox("Patient", ["All"] + patient_ids, index=1)

with col2:
    entities = sorted(mentions_df["entity_normalized"].unique())
    selected_entity = st.selectbox("Symptom / Entity", ["All"] + entities)

with col3:
    contexts = sorted(mentions_df["context"].unique())
    selected_contexts = st.multiselect("Context Filter", contexts, default=list(contexts))

# Apply filters
filtered = build_patient_timeline(
    mentions_df,
    patient_id=selected_pid if selected_pid != "All" else None,
    entity_filter=selected_entity if selected_entity != "All" else None,
    status_filter=selected_contexts if selected_contexts else None,
)

if filtered.empty:
    st.warning("No mentions match the current filters.")
    st.stop()

st.markdown(
    f'<p style="font-size:0.85rem;color:{T2}"><strong style="color:#e2e8f0">{len(filtered)}</strong> mention(s) found</p>',
    unsafe_allow_html=True,
)

# ── Timeline chart ─────────────────────────────────────────────────────────────
try:
    import plotly.express as px

    plot_df = filtered.copy()
    plot_df["visit_date"] = pd.to_datetime(plot_df["visit_date"], errors="coerce")
    plot_df = plot_df.dropna(subset=["visit_date"])

    if not plot_df.empty:
        st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Timeline Chart</div>', unsafe_allow_html=True)

        fig = px.scatter(
            plot_df,
            x="visit_date",
            y="entity_normalized",
            color="context",
            symbol="patient_id" if selected_pid == "All" else None,
            hover_data=["note_id", "patient_id", "sentence"],
            color_discrete_map=CONTEXT_PALETTE,
            height=380,
        )
        fig.update_traces(marker=dict(size=11, line=dict(width=1.5, color="#080c18")))
        fig.update_layout(
            **PLOTLY_LAYOUT,
            xaxis_title="Visit Date",
            yaxis_title="",
            legend_title="Context",
            legend=dict(
                bgcolor="rgba(20,30,53,0.9)",
                bordercolor=BORDER,
                borderwidth=1,
                font=dict(color=T2),
            ),
        )
        fig.update_xaxes(showgrid=True)
        fig.update_yaxes(showgrid=True)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            f'<p style="font-size:0.75rem;color:#64748b">Each dot = one mention · color = context label · hover for source sentence</p>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No datable mentions available for chart — see evidence table below.")

except ImportError:
    st.info("Plotly not installed — showing table only.")

# ── Evidence table ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Evidence Table</div>', unsafe_allow_html=True)
st.caption("Source sentences for each mention. All data is from the loaded corpus only.")

display_cols = [
    "patient_id", "note_id", "visit_date", "entity_normalized",
    "context", "time_expression", "normalized_event_date", "sentence",
]
available_cols = [c for c in display_cols if c in filtered.columns]
st.dataframe(filtered[available_cols], use_container_width=True, hide_index=True)

# ── Per-patient summary ────────────────────────────────────────────────────────
if selected_pid == "All":
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.6rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Per-Patient Summary</div>', unsafe_allow_html=True)

    summary = (
        filtered.groupby(["patient_id", "entity_normalized", "context"])
        .size()
        .reset_index(name="count")
    )

    rows_html = ""
    for _, row in summary.iterrows():
        ctx_badge = badge(row["context"], CONTEXT_COLORS)
        rows_html += (
            f'<tr style="border-bottom:1px solid {BORDER}">'
            f'<td style="padding:0.35rem 0.5rem;font-size:0.82rem;color:#64748b;white-space:nowrap">'
            f'<code style="background:{BG_CARD};padding:1px 5px;border-radius:3px;color:{T2}">{escape(str(row["patient_id"]))}</code></td>'
            f'<td style="padding:0.35rem 0.5rem;font-size:0.85rem;font-weight:500">{escape(str(row["entity_normalized"]))}</td>'
            f'<td style="padding:0.35rem 0.5rem">{ctx_badge}</td>'
            f'<td style="padding:0.35rem 0.5rem;font-size:0.85rem;color:{CYAN};font-weight:700;text-align:right">{row["count"]}</td>'
            f'</tr>'
        )

    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead><tr style="border-bottom:1px solid {BORDER}">'
        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Patient</th>'
        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Entity</th>'
        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Context</th>'
        f'<th style="padding:0.35rem 0.5rem;text-align:right;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Count</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )
