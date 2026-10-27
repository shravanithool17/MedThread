"""Review Queue — possible inconsistencies and unclear cases for human review."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import io
import uuid
import streamlit as st
import pandas as pd

from medthread.schemas import REVIEW_STATES, review_state_key
from medthread.styles import (
    THEME_CSS, escape, badge, status_badge, evidence_sentence, STATUS_COLORS,
    CYAN, TEAL, AMBER, CORAL, EMERALD, BLUE, BORDER, BG_CARD, T1, T2,
)

st.set_page_config(page_title="Review Queue — MedThread", page_icon="🔍", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)

for key, default in [
    ("notes", []), ("mentions_df", pd.DataFrame()),
    ("comparison_df", pd.DataFrame()), ("pipeline_run", False),
    ("review_states", {}), ("review_epoch", uuid.uuid4().hex),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding-bottom:1rem;border-bottom:1px solid {BORDER};margin-bottom:1.25rem">
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">🔍 Review Queue</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    Possible inconsistencies and unclear cases flagged for human review ·
    <span style="color:#f87171">All annotations are for demonstration only — not clinical record updates</span>
  </p>
</div>
""", unsafe_allow_html=True)

comparison_df = st.session_state.comparison_df

if not st.session_state.pipeline_run or comparison_df.empty:
    st.info("No analysis results yet. Load demo data or upload notes from the Home page.")
    st.stop()

# ── Filter bar ────────────────────────────────────────────────────────────────
REVIEW_STATUSES = ["possible_inconsistency", "unclear"]

col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    show_all = st.checkbox("Show all comparison results (not just review-worthy)", value=False)
with col2:
    patient_filter = st.selectbox(
        "Filter by patient",
        ["All"] + sorted(comparison_df["patient_id"].unique()),
    )
with col3:
    review_filter = st.selectbox(
        "Filter by review state",
        ["All"] + list(REVIEW_STATES),
    )

display_df = comparison_df.copy() if show_all else comparison_df[comparison_df["status"].isin(REVIEW_STATUSES)].copy()

if patient_filter != "All":
    display_df = display_df[display_df["patient_id"] == patient_filter]

review_states = st.session_state.review_states
display_df["review_state"] = display_df.apply(
    lambda row: review_states.get(
        review_state_key(row["patient_id"], row["entity"]),
        row["review_state"],
    ),
    axis=1,
)

if review_filter != "All":
    display_df = display_df[display_df["review_state"] == review_filter]

if display_df.empty:
    if show_all:
        st.info("No results match the current filter.")
    else:
        st.success("✅ No review-worthy items in the current filter. All cases look consistent.")
    st.stop()

# ── Queue summary bar ─────────────────────────────────────────────────────────
total = len(display_df)
inconsistencies = int((display_df["status"] == "possible_inconsistency").sum())
unreviewed = int((display_df["review_state"] == "unreviewed").sum())

st.markdown(f"""
<div style="display:flex;gap:1rem;margin-bottom:1.25rem;flex-wrap:wrap">
  <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:0.7rem 1.1rem;flex:1;min-width:140px">
    <div style="font-size:1.4rem;font-weight:800;color:{AMBER}">{total}</div>
    <div style="font-size:0.72rem;color:{T2};text-transform:uppercase;letter-spacing:0.06em">Items in queue</div>
  </div>
  <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:0.7rem 1.1rem;flex:1;min-width:140px">
    <div style="font-size:1.4rem;font-weight:800;color:{CORAL}">{inconsistencies}</div>
    <div style="font-size:0.72rem;color:{T2};text-transform:uppercase;letter-spacing:0.06em">Possible inconsistencies</div>
  </div>
  <div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;padding:0.7rem 1.1rem;flex:1;min-width:140px">
    <div style="font-size:1.4rem;font-weight:800;color:{T2}">{unreviewed}</div>
    <div style="font-size:0.72rem;color:{T2};text-transform:uppercase;letter-spacing:0.06em">Awaiting review</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Review cards ──────────────────────────────────────────────────────────────
for idx, row in display_df.iterrows():
    key_id = review_state_key(row["patient_id"], row["entity"])
    is_flagged = row["status"] == "possible_inconsistency"

    card_border = "rgba(248,113,113,0.3)" if is_flagged else BORDER
    card_bg = "rgba(248,113,113,0.04)" if is_flagged else BG_CARD
    entity_label = str(row["entity"]).replace("_", " ").title()

    with st.expander(
        f"{'🔴' if is_flagged else '🟡'}  {entity_label}  ·  Patient {row['patient_id']}  ·  {str(row['status']).replace('_',' ')}",
        expanded=is_flagged,
    ):
        left_col, right_col = st.columns([4, 1])

        with left_col:
            # Status + review state badges side-by-side
            REVIEW_COLORS = {
                "unreviewed":          (AMBER,   "rgba(245,158,11,0.12)"),
                "reviewed":            (EMERALD, "rgba(16,185,129,0.12)"),
                "not_a_contradiction": (TEAL,    "rgba(20,184,166,0.12)"),
                "needs_follow_up":     (BLUE,    "rgba(96,165,250,0.12)"),
            }
            current_review_state = review_states.get(key_id, row["review_state"])
            status_html = status_badge(row["status"])
            review_html = badge(current_review_state, REVIEW_COLORS)

            st.markdown(
                f'<div style="margin-bottom:0.75rem">{status_html} &nbsp; {review_html}</div>',
                unsafe_allow_html=True,
            )

            # Explanation
            st.markdown(
                f'<div style="font-size:0.88rem;color:{T1};margin-bottom:0.5rem">'
                f'<strong style="color:{T2};font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em">Explanation</strong><br>'
                f'{escape(str(row.get("explanation", "")))}</div>',
                unsafe_allow_html=True,
            )

            # Rule trace
            rule_trace = str(row.get("rule_trace", ""))
            if rule_trace:
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#64748b;font-style:italic;margin-bottom:0.75rem">'
                    f'<strong style="color:{T2};font-style:normal;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Rule trace</strong><br>'
                    f'{escape(rule_trace)}</div>',
                    unsafe_allow_html=True,
                )

            # Evidence notes
            evidence_note_ids = str(row.get("evidence_note_ids", ""))
            if evidence_note_ids.strip():
                notes_list = [n.strip() for n in evidence_note_ids.split(";") if n.strip()]
                notes_html = " &nbsp;·&nbsp; ".join(
                    f'<code style="background:#0f1729;padding:1px 6px;border-radius:3px;font-size:0.8rem;color:{CYAN}">{escape(n)}</code>'
                    for n in notes_list
                )
                st.markdown(
                    f'<div style="font-size:0.82rem;margin-bottom:0.75rem">'
                    f'<strong style="color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Evidence notes</strong><br>'
                    f'<div style="margin-top:0.3rem">{notes_html}</div></div>',
                    unsafe_allow_html=True,
                )

            # Evidence sentences
            evidence_sentences_raw = str(row.get("evidence_sentences", ""))
            if evidence_sentences_raw.strip():
                sents = [s.strip() for s in evidence_sentences_raw.split("|") if s.strip()]
                if sents:
                    st.markdown(
                        f'<strong style="color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Evidence sentences</strong>',
                        unsafe_allow_html=True,
                    )
                    for sent in sents:
                        st.markdown(evidence_sentence(sent, CORAL if is_flagged else AMBER), unsafe_allow_html=True)

        with right_col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;letter-spacing:0.08em;color:{T2};text-transform:uppercase;margin-bottom:0.5rem">Review State</div>',
                unsafe_allow_html=True,
            )
            current = review_states.get(key_id, "unreviewed")
            new_state = st.selectbox(
                "State",
                options=list(REVIEW_STATES),
                index=list(REVIEW_STATES).index(current) if current in list(REVIEW_STATES) else 0,
                key=f"review_{st.session_state.review_epoch}_{key_id}",
                label_visibility="collapsed",
            )
            if st.button(
                "Save",
                key=f"save_{st.session_state.review_epoch}_{key_id}",
                type="primary",
            ):
                st.session_state.review_states[key_id] = new_state
                st.rerun()

# ── Export ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Export</div>', unsafe_allow_html=True)

export_df = display_df.copy()
export_df["review_state"] = export_df.apply(
    lambda row: review_states.get(
        review_state_key(row["patient_id"], row["entity"]),
        row["review_state"],
    ),
    axis=1,
)

csv_buf = io.StringIO()
export_df.to_csv(csv_buf, index=False)
st.download_button(
    label="⬇  Download Review Results CSV",
    data=csv_buf.getvalue(),
    file_name="medthread_review_results.csv",
    mime="text/csv",
)
st.caption(
    "Downloaded file is for demonstration annotation only. "
    "It does not constitute a clinical record or a validated finding."
)
