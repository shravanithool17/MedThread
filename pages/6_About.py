"""About & Limitations — system overview, honest assessment, and related work."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st

from medthread.styles import (
    THEME_CSS, escape, badge, status_badge, CONTEXT_COLORS, STATUS_COLORS,
    CYAN, TEAL, AMBER, CORAL, BLUE, EMERALD, BORDER, BG_CARD, T1, T2,
)

st.set_page_config(page_title="About — MedThread", page_icon="ℹ️", layout="wide")
st.markdown(THEME_CSS, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding-bottom:1rem;border-bottom:1px solid {BORDER};margin-bottom:1.25rem">
  <h1 style="font-size:1.7rem;font-weight:800;margin:0 0 0.25rem">ℹ️ About &amp; Limitations</h1>
  <p style="color:{T2};margin:0;font-size:0.88rem">
    System overview · honest assessment · ethical considerations · related work
  </p>
</div>
""", unsafe_allow_html=True)

# ── Identity block ─────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1.5rem">
  <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin-bottom:0.5rem">MedThread</div>
  <div style="font-size:0.85rem;color:{T2};line-height:1.7">
    <strong style="color:#e2e8f0">Full name:</strong> Longitudinal Clinical Text Mining &amp; Consistency Analysis System<br>
    <strong style="color:#e2e8f0">Type:</strong> Educational college mini-project · NLP research prototype<br>
    <strong style="color:#e2e8f0">Version:</strong> 0.1.0<br>
    <strong style="color:#e2e8f0">Stack:</strong> Python 3.15 · Streamlit · pandas · Plotly · scikit-learn · pytest<br>
    <strong style="color:#e2e8f0">NLP:</strong> Rule-based (no machine learning model training required)<br>
    <strong style="color:#e2e8f0">Data:</strong> 15 synthetic notes across 5 demo patients — all explicitly labelled SYNTHETIC<br>
    <strong style="color:#e2e8f0">Tests:</strong> 66 automated tests across 5 test modules (pytest)
  </div>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

# ── Pipeline overview ─────────────────────────────────────────────────────────
with col1:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Six-Stage Pipeline</div>', unsafe_allow_html=True)

    stages = [
        ("1", "Preprocessing", "preprocessing.py", "Sentence split, lowercase normalisation"),
        ("2", "Entity Extraction", "entity_extraction.py", "Regex lexicon with word-boundary matching, longest-match-first"),
        ("3", "Context Detection", "context_detection.py", "Clause-scoped negation / uncertainty / resolution cue matching"),
        ("4", "Temporal Analysis", "temporal.py", "12 regex patterns, relative date resolution against visit_date"),
        ("5", "Longitudinal Analysis", "longitudinal_analysis.py", "Cross-visit comparison, temporal change vs contradiction distinction"),
        ("6", "Text Mining", "text_mining.py", "Frequency, distribution, timeline aggregation"),
    ]
    for num, name, module, desc in stages:
        st.markdown(f"""
<div style="display:flex;gap:0.75rem;align-items:flex-start;margin-bottom:0.65rem">
  <div style="min-width:1.6rem;height:1.6rem;background:rgba(34,211,238,0.12);border:1px solid rgba(34,211,238,0.3);
              border-radius:50%;display:flex;align-items:center;justify-content:center;
              font-size:0.72rem;font-weight:700;color:{CYAN};flex-shrink:0;margin-top:0.1rem">{escape(num)}</div>
  <div>
    <div style="font-size:0.88rem;font-weight:600;color:#e2e8f0">{escape(name)}</div>
    <div style="font-size:0.75rem;color:#64748b;font-family:monospace">{escape(module)}</div>
    <div style="font-size:0.82rem;color:{T2}">{escape(desc)}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Context Labels</div>', unsafe_allow_html=True)
    context_descs = {
        "affirmed":  "Symptom/condition present in the text — no negation or uncertainty found",
        "negated":   "Explicitly denied in the clause (no fever, denies pain, without cough…)",
        "uncertain": "Hedged in the clause (possible, suspected, may have, rule out…)",
        "resolved":  "Textual evidence of resolution (resolved, no longer, has cleared…)",
        "unclear":   "Cannot determine context with available cues",
    }
    for ctx, desc in context_descs.items():
        st.markdown(
            f'<div style="display:flex;gap:0.6rem;align-items:flex-start;margin-bottom:0.45rem">'
            f'{badge(ctx, CONTEXT_COLORS)}'
            f'<span style="font-size:0.82rem;color:{T2}">{escape(desc)}</span></div>',
            unsafe_allow_html=True,
        )

# ── Limitations ───────────────────────────────────────────────────────────────
with col2:
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Capabilities &amp; Limitations</div>', unsafe_allow_html=True)

    capabilities = [
        ("✅", EMERALD, "Identifies 12 canonical symptom/condition types from a configurable lexicon"),
        ("✅", EMERALD, "Distinguishes affirmed / negated / uncertain / resolved per mention"),
        ("✅", EMERALD, "Separates temporal change from possible contradiction"),
        ("✅", EMERALD, "Traces every output to its source sentence and rule"),
        ("✅", EMERALD, "Evaluates against human-authored gold annotations"),
        ("⚠", AMBER,   "Rule-based NLP has limited precision — negation scope errors can occur"),
        ("⚠", AMBER,   "Temporal normalisation is approximate and may be incorrect"),
        ("⚠", AMBER,   "Lexicon coverage is small — rare synonyms may be missed"),
        ("⚠", AMBER,   "Metrics are on a tiny synthetic benchmark (≈60 gold instances)"),
        ("❌", CORAL,   "Does NOT diagnose any medical condition"),
        ("❌", CORAL,   "Does NOT predict treatment outcomes or disease progression"),
        ("❌", CORAL,   "Does NOT replace clinical judgment or documentation review"),
        ("❌", CORAL,   "Does NOT claim clinical accuracy on real patient data"),
        ("❌", CORAL,   "NOT a medical device — not validated, not approved for clinical use"),
    ]
    for icon, color, text in capabilities:
        st.markdown(
            f'<div style="display:flex;gap:0.5rem;align-items:flex-start;margin-bottom:0.4rem">'
            f'<span style="color:{color};flex-shrink:0;font-size:0.9rem">{icon}</span>'
            f'<span style="font-size:0.83rem;color:{T2}">{escape(text)}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Privacy &amp; Data Notice</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div style="background:rgba(248,113,113,0.06);border:1px solid rgba(248,113,113,0.2);
            border-radius:8px;padding:0.85rem 1rem;font-size:0.83rem;color:{T2}">
  <strong style="color:#f87171">Do not upload identifiable patient data.</strong><br><br>
  This application is a prototype and provides <strong style="color:#e2e8f0">no data security guarantees</strong>.
  All demo data is explicitly labelled SYNTHETIC.<br><br>
  Raw note text exists <strong style="color:#e2e8f0">only in the browser session</strong> and is not
  persisted to disk or transmitted to any external service.
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Related work ──────────────────────────────────────────────────────────────
st.markdown(f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;color:{CYAN};text-transform:uppercase;margin-bottom:0.75rem;padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">Related Work &amp; Prior Art</div>', unsafe_allow_html=True)

with st.expander("Comparison with related NLP systems"):
    st.markdown("""
| Feature | NegEx/ConText | Clinical TempEval | **MedThread** |
|---|---|---|---|
| Negation detection | ✅ validated | ✅ | ✅ rule-based (unvalidated) |
| Uncertainty detection | ✅ (ConText) | partial | ✅ rule-based |
| Temporal extraction | partial | ✅ validated | ✅ simple regex |
| Longitudinal comparison | ❌ | ❌ | ✅ |
| Temporal change vs contradiction | ❌ | ❌ | ✅ |
| Evidence tracing | ❌ | ❌ | ✅ |
| Open-source Python | ✅ variants | partial | ✅ |
| Clinically validated | ✅ published | ✅ published | ❌ |

**References**
- Chapman et al. (2001) — NegEx, *Journal of Biomedical Informatics*
- Harkema et al. (2009) — ConText, extending NegEx with temporal context
- Bethard et al. (2015–2017) — Clinical TempEval shared tasks, SemEval
""")

with st.expander("Novelty statement & checklist"):
    st.markdown(f"""
**\"First ever\" is NOT supported** unless a thorough literature review is completed.

Before asserting novelty:
- [ ] PubMed: `"clinical NLP" AND "temporal" AND "longitudinal"`
- [ ] ACL Anthology: `clinical temporal extraction`, `longitudinal patient representation NLP`
- [ ] IEEE/ACM: `clinical text mining longitudinal`, `EHR NLP consistency checking`
- [ ] GitHub: `clinical NLP longitudinal consistency`
- [ ] i2b2/n2c2 challenge systems (2010, 2012, 2014)

**Honest scoped claim (if literature review finds no prior system combining all four):**

> *"An explainable rule-based pipeline that distinguishes temporal change from contradiction,
> with evidence tracing per result, evaluated on a documented synthetic benchmark."*

These are working hypotheses, not established novel contributions.
See `docs/RELATED_WORK.md` for the full checklist.
""")

# ── Run info ──────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="font-size:0.78rem;color:#475569;text-align:center">
  MedThread v0.1.0 · Python 3.15 · Streamlit ·
  Rule-based NLP only (no ML model training) ·
  <span style="color:{CORAL}">Not a medical device</span> ·
  All data is synthetic
</div>
""", unsafe_allow_html=True)
