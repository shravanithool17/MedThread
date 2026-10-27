"""Shared design system — CSS tokens and HTML helpers for MedThread UI."""
import html as _html
import re
from typing import Any


# ── Palette ──────────────────────────────────────────────────────────────────
CYAN    = "#22d3ee"
TEAL    = "#14b8a6"
EMERALD = "#10b981"
AMBER   = "#f59e0b"
CORAL   = "#f87171"
BLUE    = "#60a5fa"
PURPLE  = "#a78bfa"
MUTED   = "#94a3b8"
DIM     = "#64748b"
BG_CARD = "#141e35"
BORDER  = "#1e2d4a"
T1      = "#e2e8f0"
T2      = "#94a3b8"


CONTEXT_COLORS: dict[str, tuple[str, str]] = {
    "affirmed":  (EMERALD, "rgba(16,185,129,0.12)"),
    "negated":   (CORAL,   "rgba(248,113,113,0.12)"),
    "uncertain": (AMBER,   "rgba(245,158,11,0.12)"),
    "resolved":  (TEAL,    "rgba(20,184,166,0.12)"),
    "unclear":   (MUTED,   "rgba(148,163,184,0.12)"),
}

STATUS_COLORS: dict[str, tuple[str, str]] = {
    "possible_inconsistency": (CORAL,   "rgba(248,113,113,0.12)"),
    "unclear":                (AMBER,   "rgba(245,158,11,0.12)"),
    "persistent_documented":  (EMERALD, "rgba(16,185,129,0.12)"),
    "newly_reported":         (BLUE,    "rgba(96,165,250,0.12)"),
    "explicitly_resolved":    (TEAL,    "rgba(20,184,166,0.12)"),
    "explicitly_negated":     (MUTED,   "rgba(148,163,184,0.12)"),
    "not_documented":         (DIM,     "rgba(100,116,139,0.12)"),
}

PLOTLY_LAYOUT: dict[str, Any] = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=T2, family="system-ui,-apple-system,sans-serif", size=12),
    xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
    yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=BORDER, borderwidth=1),
)

CONTEXT_PALETTE = {
    "affirmed":  EMERALD,
    "negated":   CORAL,
    "uncertain": AMBER,
    "resolved":  TEAL,
    "unclear":   MUTED,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def escape(text: str) -> str:
    """Escape user-supplied text for safe embedding in HTML."""
    return _html.escape(str(text), quote=True)


def badge(label: str, palette: dict | None = None) -> str:
    """Inline-styled coloured badge for a context or status label."""
    colors = palette or CONTEXT_COLORS
    color, bg = colors.get(label, (MUTED, "rgba(148,163,184,0.12)"))
    text = escape(label.replace("_", " "))
    return (
        f'<span style="display:inline-block;padding:0.2em 0.6em;border-radius:999px;'
        f'font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;'
        f'color:{color};background:{bg};border:1px solid {color}50">{text}</span>'
    )


def status_badge(label: str) -> str:
    return badge(label, STATUS_COLORS)


def stat_tile(value, label: str, color: str = CYAN) -> str:
    """Single stat tile HTML."""
    return (
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:10px;'
        f'padding:1.1rem 1.25rem;text-align:center">'
        f'<div style="font-size:1.85rem;font-weight:800;color:{color};line-height:1">'
        f'{escape(str(value))}</div>'
        f'<div style="font-size:0.7rem;color:{T2};text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-top:0.3rem">{escape(label)}</div>'
        f'</div>'
    )


def section_header(title: str) -> str:
    return (
        f'<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{CYAN};margin-bottom:0.6rem;'
        f'padding-bottom:0.35rem;border-bottom:1px solid rgba(34,211,238,0.15)">'
        f'{escape(title)}</div>'
    )


def card(content_html: str, flagged: bool = False) -> str:
    border_color = "rgba(248,113,113,0.25)" if flagged else BORDER
    bg_color = "rgba(248,113,113,0.05)" if flagged else BG_CARD
    return (
        f'<div style="background:{bg_color};border:1px solid {border_color};'
        f'border-radius:10px;padding:1.1rem 1.3rem;margin-bottom:0.75rem">'
        f'{content_html}</div>'
    )


def evidence_sentence(text: str, border_color: str = AMBER) -> str:
    return (
        f'<div style="background:#0f1729;border-left:3px solid {border_color};'
        f'padding:0.5rem 0.75rem;border-radius:0 4px 4px 0;font-size:0.87rem;'
        f'color:{T1};margin:0.35rem 0;font-style:italic">'
        f'{escape(text)}</div>'
    )


def mono(text: str) -> str:
    return (
        f'<code style="background:{BG_CARD};border:1px solid {BORDER};'
        f'padding:0.1em 0.45em;border-radius:4px;font-size:0.82rem;color:{T2}">'
        f'{escape(text)}</code>'
    )


def highlight_entities(text: str, lexicon: dict) -> str:
    """Escape note text then wrap entity mentions in <mark> tags."""
    escaped = _html.escape(text)
    all_terms = sorted(
        {term for terms in lexicon.values() for term in terms},
        key=len, reverse=True,
    )
    for term in all_terms:
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        escaped = pattern.sub(
            lambda m: (
                f'<mark style="background:rgba(34,211,238,0.15);color:{CYAN};'
                f'border-radius:3px;padding:0 3px;font-weight:600">'
                f'{_html.escape(m.group())}</mark>'
            ),
            escaped,
        )
    return escaped


# ── CSS injected into every page ─────────────────────────────────────────────

THEME_CSS = f"""<style>
/* ── Shell overrides (supplements config.toml) ── */
.stApp, [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"], .main {{
    background: #080c18 !important;
}}
section[data-testid="stSidebar"] {{
    background: #0a1220 !important;
    border-right: 1px solid {BORDER} !important;
}}
.main .block-container {{ padding-top: 1.25rem !important; padding-bottom: 3rem !important; }}

/* ── Typography ── */
h1, h2, h3, h4 {{ color: {T1} !important; }}
.stCaption, .stCaption p {{ color: {T2} !important; }}

/* ── Widgets ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    background: {BG_CARD} !important;
    color: {T1} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
}}
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    background: {BG_CARD} !important;
    color: {T1} !important;
    border-color: {BORDER} !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] button[role="tab"] {{
    color: {T2} !important;
    background: transparent !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    color: {CYAN} !important;
    border-bottom: 2px solid {CYAN} !important;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}}
[data-testid="stMetricLabel"] {{ color: {T2} !important; }}
[data-testid="stMetricValue"] {{ color: {CYAN} !important; }}

/* ── Buttons ── */
.stButton > button {{
    border-radius: 6px !important;
    transition: opacity 0.15s !important;
}}
.stButton > button:hover {{ opacity: 0.85 !important; }}
[data-testid="stDownloadButton"] > button {{
    background: transparent !important;
    border: 1px solid {TEAL} !important;
    color: {TEAL} !important;
    border-radius: 6px !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
[data-testid="stExpander"] > div {{
    background: {BG_CARD} !important;
}}
[data-testid="stExpander"] summary span {{ color: {T1} !important; }}

/* ── Alerts ── */
[data-testid="stNotificationContentInfo"]    {{ background: rgba(96,165,250,0.08) !important; border-left: 3px solid {BLUE} !important; }}
[data-testid="stNotificationContentSuccess"] {{ background: rgba(16,185,129,0.08) !important; border-left: 3px solid {EMERALD} !important; }}
[data-testid="stNotificationContentWarning"] {{ background: rgba(245,158,11,0.08) !important; border-left: 3px solid {AMBER} !important; }}
[data-testid="stNotificationContentError"]   {{ background: rgba(248,113,113,0.08) !important; border-left: 3px solid {CORAL} !important; }}

/* ── Divider ── */
hr {{ border-color: {BORDER} !important; opacity: 1 !important; }}

/* ── Sidebar nav ── */
[data-testid="stSidebarNavLink"] {{ color: {T2} !important; border-radius: 6px !important; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
    color: {CYAN} !important;
    background: rgba(34,211,238,0.08) !important;
}}
</style>"""
