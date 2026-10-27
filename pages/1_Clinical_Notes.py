"""Clinical Notes — upload, view, and analyse notes."""

import sys
import os
import uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import pandas as pd
from datetime import date

from medthread.validation import load_notes_from_csv, load_notes_from_json, parse_date
from medthread.schemas import Note
from medthread.pipeline import run_pipeline
from medthread.styles import (
    THEME_CSS, escape, badge, status_badge, highlight_entities,
    CYAN, TEAL, BORDER, T2, BG_CARD, CONTEXT_COLORS,
)

st.set_page_config(page_title="Clinical Notes — MedThread", page_icon="📋", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)

for key, default in [
    ("notes", []), ("mentions_df", pd.DataFrame()),
    ("comparison_df", pd.DataFrame()), ("pipeline_run", False),
    ("review_states", {}), ("review_epoch", uuid.uuid4().hex),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding-bottom:1rem;border-bottom:1px solid {BORDER};margin-bottom:1.25rem">
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">📋 Clinical Notes</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    Upload or enter synthetic / de-identified notes · All data is session-only
  </p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:rgba(248,113,113,0.06);border:1px solid rgba(248,113,113,0.2);
            border-radius:8px;padding:0.6rem 1rem;font-size:0.8rem;color:{T2};margin-bottom:1rem">
  ⚠ <strong style="color:#f87171">SYNTHETIC / DE-IDENTIFIED DATA ONLY.</strong>
  Raw note text is never stored permanently — it exists only in this browser session.
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📁  Upload CSV / JSON", "✏️  Manual Entry", "📄  View Loaded Notes"])

# ── Tab 1: Upload ─────────────────────────────────────────────────────────────
with tab1:
    st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;
            padding:1rem 1.25rem;margin-bottom:1rem;font-size:0.85rem;color:{T2}">
  <strong style="color:#e2e8f0">Required columns:</strong>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">patient_id</code>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">note_id</code>
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">visit_date</code> (YYYY-MM-DD)
  <code style="background:#080c18;padding:1px 5px;border-radius:3px;color:{CYAN}">text</code>
</div>
""", unsafe_allow_html=True)

    uploaded = st.file_uploader("Choose a CSV or JSON file", type=["csv", "json"], key="note_upload")
    if uploaded is not None:
        content = uploaded.read()
        if uploaded.name.endswith(".json"):
            notes, errors = load_notes_from_json(content)
        else:
            notes, errors = load_notes_from_csv(content)

        for err in errors:
            st.warning(err)
        if notes:
            st.success(f"Parsed {len(notes)} notes successfully.")
            if st.button("▶  Run NLP Pipeline on Uploaded Notes", type="primary"):
                with st.spinner("Running pipeline…"):
                    st.session_state.notes = notes
                    mentions_df, comparison_df = run_pipeline(notes)
                    st.session_state.mentions_df = mentions_df
                    st.session_state.comparison_df = comparison_df
                    st.session_state.pipeline_run = True
                    st.session_state.review_states = {}
                    st.session_state.review_epoch = uuid.uuid4().hex
                st.success("Pipeline complete. Navigate to other pages to explore results.")
        elif not errors:
            st.info("No valid notes found in the file.")

# ── Tab 2: Manual Entry ───────────────────────────────────────────────────────
with tab2:
    st.markdown(f'<p style="color:{T2};font-size:0.88rem">Add a single synthetic note to the current session.</p>', unsafe_allow_html=True)
    with st.form("manual_note_form"):
        col1, col2 = st.columns(2)
        with col1:
            patient_id = st.text_input("Patient ID (synthetic/demo only)", value="DEMO_P099")
            note_id = st.text_input("Note ID", value="NOTE_099")
        with col2:
            visit_date_input = st.date_input("Visit Date", value=date.today())
            visit_date_str = visit_date_input.strftime("%Y-%m-%d") if visit_date_input else ""
        note_text = st.text_area(
            "Note Text",
            height=160,
            placeholder="Enter synthetic clinical note text here…",
        )
        submitted = st.form_submit_button("Add Note & Re-run Pipeline", type="primary")

    if submitted:
        errors = []
        if not patient_id.strip():
            errors.append("Patient ID is required.")
        if not note_id.strip():
            errors.append("Note ID is required.")
        if not note_text.strip():
            errors.append("Note text is required.")
        existing_ids = {n.note_id for n in st.session_state.notes}
        if note_id.strip() in existing_ids:
            errors.append(f"Note ID '{note_id}' already exists in this session.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            new_note = Note(
                patient_id=patient_id.strip(),
                note_id=note_id.strip(),
                visit_date=parse_date(visit_date_str),
                text=note_text.strip(),
            )
            st.session_state.notes.append(new_note)
            with st.spinner("Re-running pipeline…"):
                mentions_df, comparison_df = run_pipeline(st.session_state.notes)
                st.session_state.mentions_df = mentions_df
                st.session_state.comparison_df = comparison_df
                st.session_state.pipeline_run = True
                st.session_state.review_states = {}
                st.session_state.review_epoch = uuid.uuid4().hex
            st.success(f"Note {escape(note_id)} added. Pipeline updated.")

# ── Tab 3: View Loaded Notes ──────────────────────────────────────────────────
with tab3:
    notes = st.session_state.notes
    if not notes:
        st.info("No notes loaded. Use the Upload tab or load demo data from the Home page.")
        st.stop()

    st.markdown(
        f'<p style="color:{T2};font-size:0.88rem"><strong style="color:#e2e8f0">{len(notes)}</strong> notes loaded in this session.</p>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 2])
    with col1:
        patient_ids = sorted({n.patient_id for n in notes})
        selected_pid = st.selectbox("Filter by Patient", ["All"] + patient_ids)
    with col2:
        show_highlights = st.toggle("Highlight entity mentions", value=True)

    filtered_notes = [
        n for n in notes
        if selected_pid == "All" or n.patient_id == selected_pid
    ]

    if not filtered_notes:
        st.warning("No notes match this filter.")
        st.stop()

    # Summary table
    rows = [
        {
            "Patient ID": n.patient_id,
            "Note ID": n.note_id,
            "Visit Date": str(n.visit_date) if n.visit_date else "Unknown",
            "Preview": (n.text[:100] + "…") if len(n.text) > 100 else n.text,
        }
        for n in filtered_notes
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Full Note Viewer</div>', unsafe_allow_html=True)

    selected_note_id = st.selectbox(
        "Select note",
        options=[n.note_id for n in filtered_notes],
        key="view_note_select",
    )

    if selected_note_id:
        note_obj = next((n for n in filtered_notes if n.note_id == selected_note_id), None)
        if note_obj:
            # Metadata row
            st.markdown(
                f'<div style="font-size:0.82rem;color:{T2};margin-bottom:0.75rem">'
                f'Note <code style="color:{CYAN}">{escape(note_obj.note_id)}</code> · '
                f'Patient <code style="color:{CYAN}">{escape(note_obj.patient_id)}</code> · '
                f'Date <strong style="color:#e2e8f0">{escape(str(note_obj.visit_date or "Unknown"))}</strong>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Note text — with optional entity highlighting
            if show_highlights:
                try:
                    from medthread.config import SYMPTOM_LEXICON
                    highlighted = highlight_entities(note_obj.text, SYMPTOM_LEXICON)
                    st.markdown(
                        f'<div style="background:#0f1729;border:1px solid {BORDER};border-radius:8px;'
                        f'padding:1rem;font-size:0.9rem;line-height:1.7;max-height:320px;'
                        f'overflow-y:auto;white-space:pre-wrap;word-break:break-word">'
                        f'{highlighted}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<p style="font-size:0.75rem;color:{T2};margin-top:0.35rem">'
                        f'<mark style="background:rgba(34,211,238,0.15);color:{CYAN};border-radius:2px;padding:0 3px">highlighted</mark>'
                        f' = entity mention recognised by the lexicon</p>',
                        unsafe_allow_html=True,
                    )
                except Exception:
                    st.text_area("Full note text (read-only)", value=note_obj.text,
                                  height=220, disabled=True, key="full_note_text")
            else:
                st.text_area("Full note text (read-only)", value=note_obj.text,
                              height=220, disabled=True, key="full_note_text_plain")

            # Mentions from this note (if pipeline has run)
            if st.session_state.pipeline_run and not st.session_state.mentions_df.empty:
                mdf = st.session_state.mentions_df
                note_mentions = mdf[mdf["note_id"] == selected_note_id]
                if not note_mentions.empty:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.5rem">Extracted Mentions ({len(note_mentions)})</div>', unsafe_allow_html=True)
                    rows_html = ""
                    for _, row in note_mentions.iterrows():
                        ctx_badge = badge(row.get("context", "unclear"), CONTEXT_COLORS)
                        entity_text = escape(str(row.get("entity_normalized", "")))
                        sentence_text = escape(str(row.get("sentence", "")))
                        reason_text = escape(str(row.get("reason", "")))
                        rows_html += (
                            f'<tr style="border-bottom:1px solid {BORDER}">'
                            f'<td style="padding:0.4rem 0.5rem;font-weight:600;font-size:0.85rem;white-space:nowrap">{entity_text}</td>'
                            f'<td style="padding:0.4rem 0.5rem">{ctx_badge}</td>'
                            f'<td style="padding:0.4rem 0.5rem;font-size:0.82rem;color:{T2};font-style:italic">{sentence_text}</td>'
                            f'<td style="padding:0.4rem 0.5rem;font-size:0.78rem;color:#64748b">{reason_text}</td>'
                            f'</tr>'
                        )
                    st.markdown(
                        f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem">'
                        f'<thead><tr style="border-bottom:1px solid {BORDER}">'
                        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Entity</th>'
                        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Context</th>'
                        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Sentence</th>'
                        f'<th style="padding:0.35rem 0.5rem;text-align:left;color:{T2};font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em">Reason</th>'
                        f'</tr></thead><tbody>{rows_html}</tbody></table>',
                        unsafe_allow_html=True,
                    )
