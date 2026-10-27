"""MedThread — Overview / Command Center."""

import sys
import os
import uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
import pandas as pd

from medthread.config import APP_TITLE, SAFETY_NOTICE
from medthread.validation import load_notes_from_csv
from medthread.pipeline import run_pipeline
from medthread.text_mining import compute_corpus_stats
from medthread.styles import THEME_CSS, escape, stat_tile, CYAN, EMERALD, CORAL, AMBER, TEAL, BLUE

st.set_page_config(
    page_title="MedThread",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("notes", []), ("mentions_df", pd.DataFrame()),
    ("comparison_df", pd.DataFrame()), ("pipeline_run", False),
    ("review_states", {}), ("review_epoch", uuid.uuid4().hex),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def load_synthetic_data():
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'synthetic_notes.csv')
    with open(data_path, 'r', encoding='utf-8') as f:
        content = f.read()
    notes, errors = load_notes_from_csv(content)
    if errors:
        st.warning(f"Notes about the data: {errors}")
    st.session_state.notes = notes
    mentions_df, comparison_df = run_pipeline(notes)
    st.session_state.mentions_df = mentions_df
    st.session_state.comparison_df = comparison_df
    st.session_state.pipeline_run = True
    st.session_state.review_states = {}
    st.session_state.review_epoch = uuid.uuid4().hex
    return notes, errors


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
<div style="padding:0.75rem 0 1.25rem">
  <div style="font-size:1.35rem;font-weight:800;color:{CYAN};letter-spacing:-0.01em">🧬 MedThread</div>
  <div style="font-size:0.73rem;color:#64748b;margin-top:0.2rem;letter-spacing:0.03em">
    LONGITUDINAL CLINICAL NLP
  </div>
</div>
""", unsafe_allow_html=True)

    st.divider()
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.5rem">Quick Actions</div>', unsafe_allow_html=True)

    if st.button("▶  Load Demo Data (Synthetic)", type="primary", use_container_width=True):
        with st.spinner("Running NLP pipeline on synthetic notes…"):
            notes, _ = load_synthetic_data()
        st.success(f"Loaded {len(notes)} synthetic notes.")

    if st.session_state.pipeline_run:
        if st.button("↺  Reset Session", use_container_width=True):
            if not st.session_state.get("reset_confirmed"):
                st.session_state.reset_confirmed = True
                st.warning("Click Reset again to confirm.")
            else:
                for key in ["notes", "mentions_df", "comparison_df",
                    "pipeline_run", "reset_confirmed", "review_states",
                    "review_epoch"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    st.divider()
    st.markdown(f"""
<div style="font-size:0.75rem;color:#64748b;line-height:1.7">
  <strong style="color:#94a3b8">Pages</strong><br>
  🏠 Overview &amp; Stats<br>
  📋 Clinical Notes<br>
  📅 Patient Timeline<br>
  🔍 Review Queue<br>
  📊 Text Mining<br>
  📐 Evaluation<br>
  ℹ️ About &amp; Limitations
</div>
""", unsafe_allow_html=True)


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:1.75rem 0 1rem">
  <div style="font-size:2.2rem;font-weight:800;margin:0 0 0.3rem;
              background:linear-gradient(90deg,{CYAN} 0%,{TEAL} 100%);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text">MedThread</div>
  <div style="font-size:1.05rem;color:#94a3b8;font-style:italic;margin:0 0 1rem">
    See the story behind the notes.
  </div>
  <div style="background:rgba(248,113,113,0.07);border:1px solid rgba(248,113,113,0.22);
              border-radius:8px;padding:0.65rem 1rem;font-size:0.81rem;color:#94a3b8;
              display:inline-block">
    ⚠ <strong style="color:#f87171">SYNTHETIC DATA ONLY</strong> — Educational prototype.
    Not a medical device. Do not upload real patient data.
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stat tiles ────────────────────────────────────────────────────────────────
if st.session_state.pipeline_run:
    stats = compute_corpus_stats(
        st.session_state.mentions_df,
        st.session_state.comparison_df,
        st.session_state.notes,
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(stat_tile(stats["n_patients"], "Patients", CYAN), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_tile(stats["n_notes"], "Notes", TEAL), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_tile(stats["n_mentions"], "Mentions", BLUE), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_tile(stats["n_review_flags"], "Review Flags", AMBER), unsafe_allow_html=True)
    with c5:
        st.markdown(stat_tile(stats["n_possible_inconsistency"], "Inconsistencies", CORAL), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
else:
    st.markdown(f"""
<div style="background:#141e35;border:1px dashed #1e2d4a;border-radius:10px;
            padding:1.25rem 1.5rem;text-align:center;color:#64748b;margin-bottom:1rem">
  Click <strong style="color:{CYAN}">▶ Load Demo Data</strong> in the sidebar to run the
  pipeline on 15 synthetic notes across 5 demo patients.
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Body ──────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">What is MedThread?</div>', unsafe_allow_html=True)
    st.markdown("""
MedThread is an **educational NLP prototype** that processes synthetic clinical notes
through a six-stage rule-based pipeline:

| Stage | Module | What it does |
|---|---|---|
| Preprocessing | `preprocessing` | Sentence split, normalize case |
| Entity extraction | `entity_extraction` | Regex lexicon matching (word-boundary) |
| Context detection | `context_detection` | Clause-scoped negation / uncertainty / resolution |
| Temporal | `temporal` | Links mentions to dates/time expressions |
| Longitudinal | `longitudinal_analysis` | Cross-visit comparison, status assignment |
| Mining | `text_mining` | Frequency, distribution, timeline views |
""")

    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin:1.25rem 0 0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Cross-Visit Status Types</div>', unsafe_allow_html=True)

    from medthread.styles import status_badge
    rows_html = ""
    status_descriptions = {
        "newly_reported":         "First documented in this record",
        "persistent_documented":  "Affirmed across multiple notes",
        "explicitly_resolved":    "Textual evidence of resolution present",
        "explicitly_negated":     "Explicitly denied in the text",
        "possible_inconsistency": "Conflicting claims — needs human review",
        "unclear":                "Ambiguous or insufficient evidence",
        "not_documented":         "Not mentioned (absence ≠ absence of condition)",
    }
    for s, desc in status_descriptions.items():
        rows_html += (
            f'<tr><td style="padding:0.3rem 0.5rem">{status_badge(s)}</td>'
            f'<td style="padding:0.3rem 0.5rem;font-size:0.85rem;color:#94a3b8">{escape(desc)}</td></tr>'
        )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse">{rows_html}</table>',
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Pipeline Architecture</div>', unsafe_allow_html=True)

    if st.session_state.pipeline_run and not st.session_state.mentions_df.empty:
        mdf = st.session_state.mentions_df
        cdf = st.session_state.comparison_df

        # Context breakdown mini-table
        if not mdf.empty and "context" in mdf.columns:
            ctx_counts = mdf["context"].value_counts()
            from medthread.styles import badge as ctx_badge, CONTEXT_COLORS
            rows = ""
            for ctx, cnt in ctx_counts.items():
                rows += (
                    f'<tr><td style="padding:0.3rem 0.5rem">{ctx_badge(ctx, CONTEXT_COLORS)}</td>'
                    f'<td style="padding:0.3rem 0.5rem;text-align:right;font-size:0.85rem;color:{CYAN};font-weight:700">{cnt}</td></tr>'
                )
            st.markdown(
                f'<div style="font-size:0.8rem;color:#94a3b8;margin-bottom:0.4rem">Context label counts</div>'
                f'<table style="width:100%;border-collapse:collapse">{rows}</table>',
                unsafe_allow_html=True,
            )
        st.markdown("<br>", unsafe_allow_html=True)
        if not cdf.empty and "status" in cdf.columns:
            flag_count = int((cdf["status"] == "possible_inconsistency").sum())
            review_count = int(cdf["status"].isin(["possible_inconsistency", "unclear"]).sum())
            st.markdown(
                f'<div style="background:#141e35;border:1px solid #1e2d4a;border-radius:8px;padding:0.85rem 1rem">'
                f'<div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em">Longitudinal flags</div>'
                f'<div style="margin-top:0.5rem;font-size:0.88rem;color:#e2e8f0">'
                f'<span style="color:{CORAL};font-weight:700">{flag_count}</span> possible inconsistenc{"y" if flag_count==1 else "ies"} · '
                f'<span style="color:{AMBER};font-weight:700">{review_count}</span> items in review queue'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(f"""
<div style="background:#141e35;border:1px solid #1e2d4a;border-radius:8px;padding:1rem">
  <div style="font-size:0.8rem;color:#64748b;margin-bottom:0.5rem">Six-stage rule-based pipeline</div>
  {"".join(
      f'<div style="font-size:0.82rem;color:#94a3b8;padding:0.2rem 0">→ {escape(s)}</div>'
      for s in ["Preprocessing", "Entity Extraction", "Context Detection",
                "Temporal Analysis", "Longitudinal Analysis", "Text Mining"]
  )}
  <div style="margin-top:0.75rem;font-size:0.78rem;color:#475569">
    No ML model training · Fully explainable · Evidence-traced
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("ℹ️ Limitations & Novelty Statement"):
        st.markdown(f"""
**What MedThread does NOT do**
- Diagnose any condition
- Predict outcomes or disease progression
- Replace clinical judgment
- Claim clinical accuracy on real data

**Honest Novelty Statement**
Longitudinal clinical NLP, negation detection, and contradiction checking
are established research areas (NegEx, ConText, Clinical TempEval).

MedThread's student-project contribution:
1. Explainable pipeline with per-result rule trace
2. Explicit distinction between temporal change and contradiction
3. Documented synthetic benchmark with computed metrics

See `docs/RELATED_WORK.md` for the full literature checklist.

**Privacy:** Do not upload identifiable patient data.
All demo data is labeled SYNTHETIC.
""")
