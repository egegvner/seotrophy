import datetime as dt
import html
import json
from typing import Any
import base64

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import SEOAuditReport
from utils import (
    _build_audit_pdf,
    cached_favicon,
    cached_site_title,
    cached_supabase,
    get_user_audits,
    get_user_audits_new,
    time_ago,
    load_audit_visual_maps,
    render_attention_map_html,
)


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard CSS
# ─────────────────────────────────────────────────────────────────────────────

PAGE_CSS = """
<style>
:root {
    --dash-bg: #f5f3ee;
    --dash-surface: #ffffff;
    --dash-surface-soft: #f8f7f3;
    --dash-ink: #171612;
    --dash-muted: #666257;
    --dash-line: #dedbd2;
    --dash-line-strong: #c8c3b8;
    --dash-gold: #b27a16;
    --dash-good: #256b4a;
    --dash-warn: #9a5a00;
    --dash-bad: #9c3931;
    --dash-info: #245f78;
    --dash-radius: 16px;
    --dash-radius-sm: 11px;
}

.stApp {
    background:
        repeating-linear-gradient(
            0deg,
            transparent,
            transparent 49px,
            rgba(23, 22, 18, 0.035) 49px,
            rgba(23, 22, 18, 0.035) 50px
        ),
        repeating-linear-gradient(
            90deg,
            transparent,
            transparent 49px,
            rgba(23, 22, 18, 0.035) 49px,
            rgba(23, 22, 18, 0.035) 50px
        ),
        var(--dash-bg);
}

header[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 96% !important;
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--dash-ink);
}

::selection { background: var(--dash-ink); color: #ffffff; }

/* Header */
.audit-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: stretch;
    margin: 0.75rem 0 0.9rem 0;
}

.audit-hero-main,
.audit-score-panel {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius);
}

.audit-hero-main {
    padding: 1.15rem 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    min-width: 0;
}

.audit-site-mark {
    width: 48px;
    height: 48px;
    border: 1px solid var(--dash-line);
    border-radius: 12px;
    background: var(--dash-surface-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
    overflow: hidden;
    font-size: 1.25rem;
}

.audit-site-mark img {
    width: 28px;
    height: 28px;
    object-fit: contain;
}

.audit-hero-copy { min-width: 0; }

.audit-title {
    margin: 0;
    font-size: clamp(1.65rem, 2.3vw, 2.45rem);
    line-height: 1.08;
    letter-spacing: -0.045em;
    color: var(--dash-ink);
    font-weight: 780;
}

.audit-url {
    display: block;
    margin-top: 0.45rem;
    color: var(--dash-muted);
    font-size: 0.96rem;
    overflow-wrap: anywhere;
    text-decoration: none;
}

.audit-url:hover { color: var(--dash-ink); text-decoration: underline; }

.audit-report-id {
    margin-top: 0.35rem;
    color: var(--dash-muted);
    font-size: 0.9rem;
}

.audit-score-panel {
    min-width: 150px;
    padding: 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.audit-score-number {
    font-size: 2.8rem;
    line-height: 1;
    font-weight: 800;
    letter-spacing: -0.065em;
}

.audit-score-state {
    margin-top: 0.35rem;
    font-size: 0.92rem;
    font-weight: 720;
}

/* Shared panels */
.dashboard-section {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius);
    padding: 1rem;
    margin-bottom: 0.75rem;
}

.dashboard-section-title {
    margin: 0 0 0.75rem 0;
    font-size: 1.08rem;
    line-height: 1.25;
    letter-spacing: -0.025em;
    font-weight: 760;
    color: var(--dash-ink);
}

.dashboard-section-body {
    font-size: 0.98rem;
    line-height: 1.58;
    color: var(--dash-ink);
    white-space: pre-wrap;
}

.dashboard-recommendation {
    margin-top: 0.75rem;
    border-left: 4px solid var(--dash-gold);
    background: #fbf6ea;
    padding: 0.8rem 0.9rem;
    border-radius: 0 var(--dash-radius-sm) var(--dash-radius-sm) 0;
    font-size: 0.98rem;
    line-height: 1.5;
}

.dashboard-heading {
    margin: 0.25rem 0 0.65rem 0;
    font-size: 1.12rem;
    font-weight: 760;
    letter-spacing: -0.025em;
    color: var(--dash-ink);
}

/* Metrics */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(var(--metric-columns, 4), minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.75rem;
}

.metric-tile {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius-sm);
    padding: 0.85rem 0.9rem;
    min-width: 0;
}

.metric-label {
    color: var(--dash-muted);
    font-size: 0.84rem;
    font-weight: 680;
    line-height: 1.2;
}

.metric-value {
    margin-top: 0.4rem;
    color: var(--dash-ink);
    font-size: 1.45rem;
    font-weight: 780;
    line-height: 1.08;
    letter-spacing: -0.04em;
    overflow-wrap: anywhere;
}

.metric-value.compact {
    font-size: 1.05rem;
    letter-spacing: -0.015em;
    line-height: 1.3;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(var(--status-columns, 4), minmax(0, 1fr));
    gap: 0.6rem;
    margin-bottom: 0.75rem;
}

.status-tile {
    border: 1px solid var(--dash-line);
    border-left: 5px solid var(--dash-line-strong);
    background: var(--dash-surface);
    border-radius: var(--dash-radius-sm);
    padding: 0.78rem 0.85rem;
    min-width: 0;
}

.status-tile.good { border-left-color: var(--dash-good); }
.status-tile.warn { border-left-color: var(--dash-warn); }
.status-tile.bad { border-left-color: var(--dash-bad); }
.status-tile.info { border-left-color: var(--dash-info); }

.status-label {
    color: var(--dash-muted);
    font-size: 0.84rem;
    font-weight: 660;
}

.status-value {
    margin-top: 0.3rem;
    color: var(--dash-ink);
    font-size: 1rem;
    font-weight: 760;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.field-grid {
    display: grid;
    grid-template-columns: repeat(var(--field-columns, 2), minmax(0, 1fr));
    gap: 0.6rem;
    margin-bottom: 0.75rem;
}

.field-item {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface-soft);
    border-radius: var(--dash-radius-sm);
    padding: 0.75rem 0.85rem;
    min-width: 0;
}

.field-label {
    color: var(--dash-muted);
    font-size: 0.84rem;
    font-weight: 670;
}

.field-value {
    margin-top: 0.3rem;
    color: var(--dash-ink);
    font-size: 0.98rem;
    font-weight: 690;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.score-grid {
    display: grid;
    grid-template-columns: repeat(var(--score-columns, 2), minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.75rem;
}

.score-row {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius-sm);
    padding: 0.8rem 0.85rem;
}

.score-row-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.94rem;
}

.score-row-label { font-weight: 690; color: var(--dash-ink); }
.score-row-value { font-weight: 780; color: var(--dash-ink); }

.score-track {
    height: 9px;
    background: #ebe8e0;
    border-radius: 999px;
    margin-top: 0.6rem;
    overflow: hidden;
}

.score-fill {
    height: 100%;
    background: var(--dash-ink);
    border-radius: 999px;
}

.tag-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.tag-chip {
    border: 1px solid var(--dash-line-strong);
    background: var(--dash-surface);
    border-radius: 999px;
    padding: 0.45rem 0.72rem;
    color: var(--dash-ink);
    font-size: 0.92rem;
    font-weight: 650;
    overflow-wrap: anywhere;
}

/* Action plan */
.action-plan-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.65rem;
}

.action-plan-card {
    border: 1px solid var(--dash-line);
    border-top: 5px solid var(--dash-ink);
    background: var(--dash-surface);
    border-radius: var(--dash-radius-sm);
    padding: 0.9rem;
}

.action-plan-card.high { border-top-color: var(--dash-bad); }
.action-plan-card.medium { border-top-color: var(--dash-warn); }
.action-plan-card.low { border-top-color: var(--dash-good); }

.action-plan-title {
    font-size: 1rem;
    font-weight: 780;
    margin-bottom: 0.65rem;
}

.action-plan-item {
    border-top: 1px solid var(--dash-line);
    padding-top: 0.6rem;
    margin-top: 0.6rem;
    font-size: 0.95rem;
    line-height: 1.45;
}

/* Streamlit controls */
button[data-baseweb="tab"] {
    font-size: 0.98rem !important;
    font-weight: 720 !important;
    padding: 0.72rem 0.78rem !important;
    margin: 0 !important;
}

[data-baseweb="tab-list"] {
    gap: 0.25rem !important;
    background: var(--dash-surface);
    border: 1px solid var(--dash-line);
    border-radius: 14px;
    padding: 0.3rem;
}

[data-baseweb="tab-highlight"] { background-color: var(--dash-ink) !important; }

[data-testid="stDownloadButton"] > button,
[data-testid="stButton"] > button {
    min-height: 44px;
    border-radius: 999px !important;
    font-weight: 720 !important;
}

[data-testid="stMetric"] {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius-sm);
    padding: 0.85rem;
}

[data-testid="stMetricLabel"] { font-size: 0.88rem; color: var(--dash-muted); }
[data-testid="stMetricValue"] { font-size: 1.4rem; color: var(--dash-ink); }

[data-testid="stDataFrame"] {
    border: 1px solid var(--dash-line);
    border-radius: var(--dash-radius-sm);
    overflow: hidden;
}

[data-testid="stPlotlyChart"] {
    border: 1px solid var(--dash-line);
    background: var(--dash-surface);
    border-radius: var(--dash-radius);
    padding: 0.25rem;
}

div[data-testid="stTextArea"] textarea {
    font-size: 0.96rem !important;
    line-height: 1.5 !important;
    background: var(--dash-surface-soft) !important;
    border: 1px solid var(--dash-line) !important;
    border-radius: var(--dash-radius-sm) !important;
}

.score-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 8px 6px;
    border-radius: 12px;
    border: 1px solid var(--dash-line);
    background: var(--dash-surface-soft);
    color: var(--dash-ink);
    text-align: center;
    min-width: 72px;
}
.score-badge .score-num { font-size: 1.55rem; font-weight: 800; line-height: 1.1; }
.score-badge .score-lbl { font-size: 0.8rem; margin-top: 2px; }
.small-muted { color: var(--dash-muted); font-size: 0.95rem; }

@media (max-width: 1200px) {
    .metric-grid { --metric-columns: 4 !important; }
    .status-grid { --status-columns: 3 !important; }
    .action-plan-grid { grid-template-columns: 1fr; }
}

@media (max-width: 850px) {
    .block-container { max-width: 100% !important; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
    .audit-hero { grid-template-columns: 1fr; }
    .audit-score-panel { min-width: 0; }
    .metric-grid { --metric-columns: 2 !important; }
    .status-grid { --status-columns: 2 !important; }
    .field-grid { --field-columns: 1 !important; }
    .score-grid { --score-columns: 1 !important; }
}

@media (max-width: 520px) {
    .metric-grid,
    .status-grid { --metric-columns: 1 !important; --status-columns: 1 !important; }
    .audit-hero-main { align-items: flex-start; }
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_json(value: Any) -> dict:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return value if isinstance(value, dict) else {}


@st.cache_data(show_spinner=False)
def _cached_audit_pdf(audit_id: str, report_json: str, scraped_json: str, page_url: str, site_title: str) -> bytes:
    report = SEOAuditReport.model_validate_json(report_json)
    scraped = _safe_json(scraped_json)
    return _build_audit_pdf(
        report=report,
        scraped=scraped,
        page_url=page_url,
        site_title=site_title,
        audit_id=audit_id,
    )


def _reset_pdf_download(audit_id) -> None:
    st.session_state.pop(f"pdf_bytes_{audit_id}", None)


def _score_color(score: int) -> str:
    if score >= 75:
        return "#256b4a"
    if score >= 50:
        return "#9a5a00"
    return "#9c3931"


def _score_label(score: int) -> str:
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Needs work"
    return "Critical"


def _bool_label(value: Any) -> str:
    return "Yes" if bool(value) else "No"


def _safe_display(value: Any, fallback: str = "Not detected") -> str:
    if value is None:
        return fallback
    if isinstance(value, str) and not value.strip():
        return fallback
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else fallback
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items()) if value else fallback
    return str(value)


def _safe_html(value: Any, fallback: str = "Not detected") -> str:
    return html.escape(_safe_display(value, fallback=fallback))


def _empty_like(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _rs_value(report, scraped: dict, key: str, fallback: Any = "Not checked") -> Any:
    value = getattr(report, key, None)
    if not _empty_like(value):
        return value
    value = scraped.get(key)
    if not _empty_like(value):
        return value
    return fallback


def _rs_int(report, scraped: dict, key: str, fallback: int = 0) -> int:
    try:
        return int(float(_rs_value(report, scraped, key, fallback)))
    except Exception:
        return fallback


def _rs_bool(report, scraped: dict, key: str, fallback: bool = False) -> bool:
    value = _rs_value(report, scraped, key, fallback)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "present", "available", "valid"}
    return bool(value)


def format_file_size(size_kb: float) -> str:
    try:
        size_kb = float(size_kb or 0)
    except Exception:
        size_kb = 0
    if size_kb < 1000:
        return f"{size_kb:.1f} KB"
    return f"{size_kb / 1000:.2f} MB"


def _normalise_score(value: Any) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except Exception:
        return 0


def _status_tone(value: Any) -> str:
    if isinstance(value, bool):
        return "good" if value else "bad"
    text = str(value).strip().lower()
    if text in {"yes", "true", "present", "valid", "good", "available", "indexable", "low"}:
        return "good"
    if any(token in text for token in ["critical", "missing", "blocked", "invalid", "error", "high", "no"]):
        return "bad"
    if any(token in text for token in ["needs", "medium", "warning", "partial"]):
        return "warn"
    return "info"


def _render_metric_grid(items: list[tuple[str, Any]], columns: int = 4) -> None:
    cards = []
    for label, value in items:
        value_text = _safe_display(value)
        compact = " compact" if len(value_text) > 18 else ""
        cards.append(
            f'<div class="metric-tile">'
            f'<div class="metric-label">{html.escape(str(label))}</div>'
            f'<div class="metric-value{compact}">{html.escape(value_text)}</div>'
            f'</div>'
        )
    st.html(f'<div class="metric-grid" style="--metric-columns:{max(1, columns)}">{"".join(cards)}</div>')


def _render_status_grid(items: list[tuple[str, Any]], columns: int = 4) -> None:
    cards = []
    for label, value in items:
        display = _safe_display(value)
        tone = _status_tone(value)
        cards.append(
            f'<div class="status-tile {tone}">'
            f'<div class="status-label">{html.escape(str(label))}</div>'
            f'<div class="status-value">{html.escape(display)}</div>'
            f'</div>'
        )
    st.html(f'<div class="status-grid" style="--status-columns:{max(1, columns)}">{"".join(cards)}</div>')


def _render_field_grid(items: list[tuple[str, Any]], columns: int = 2) -> None:
    cards = []
    for label, value in items:
        cards.append(
            f'<div class="field-item">'
            f'<div class="field-label">{html.escape(str(label))}</div>'
            f'<div class="field-value">{_safe_html(value)}</div>'
            f'</div>'
        )
    st.html(f'<div class="field-grid" style="--field-columns:{max(1, columns)}">{"".join(cards)}</div>')


def _render_score_grid(items: list[tuple[str, Any]], columns: int = 2) -> None:
    rows = []
    for label, value in items:
        score = _normalise_score(value)
        rows.append(
            f'<div class="score-row">'
            f'<div class="score-row-top">'
            f'<span class="score-row-label">{html.escape(str(label))}</span>'
            f'<span class="score-row-value">{score}</span>'
            f'</div>'
            f'<div class="score-track"><div class="score-fill" style="width:{score}%"></div></div>'
            f'</div>'
        )
    st.html(f'<div class="score-grid" style="--score-columns:{max(1, columns)}">{"".join(rows)}</div>')


def _render_text_panel(title: str, body: Any, recommendation: Any = None, recommendation_label: str = "Recommendation") -> None:
    body_html = _safe_html(body, fallback="No analysis available.")
    recommendation_html = ""
    if recommendation is not None and str(recommendation).strip():
        recommendation_html = (
            f'<div class="dashboard-recommendation"><strong>{html.escape(recommendation_label)}:</strong> '
            f'{_safe_html(recommendation)}</div>'
        )
    st.html(
        f'<section class="dashboard-section">'
        f'<h3 class="dashboard-section-title">{html.escape(title)}</h3>'
        f'<div class="dashboard-section-body">{body_html}</div>'
        f'{recommendation_html}'
        f'</section>'
    )


def _render_heading(title: str) -> None:
    st.html(f'<div class="dashboard-heading">{html.escape(title)}</div>')


def _render_tags(items: Any, fallback: str = "None detected") -> None:
    if isinstance(items, str):
        values = [items] if items.strip() else []
    elif isinstance(items, list):
        values = [str(item) for item in items if str(item).strip()]
    else:
        values = []
    if not values:
        values = [fallback]
    chips = "".join(f'<span class="tag-chip">{html.escape(item)}</span>' for item in values)
    st.html(f'<div class="tag-wrap">{chips}</div>')


def _parse_action_plan(markdown_text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = "Action plan"
    current_items: list[str] = []

    for raw_line in (markdown_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("###"):
            if current_items:
                sections.append((current_title, current_items))
                current_items = []
            current_title = line.lstrip("#").strip()
        elif line.startswith("- "):
            current_items.append(line[2:].strip())
        else:
            current_items.append(line)

    if current_items:
        sections.append((current_title, current_items))
    return sections


def _render_action_plan(markdown_text: str) -> None:
    sections = _parse_action_plan(markdown_text)
    if not sections:
        _render_text_panel("Priority action plan", "No action items were generated.")
        return

    cards = []
    for title, items in sections:
        title_lower = title.lower()
        tone = "high" if "high" in title_lower else "medium" if "medium" in title_lower else "low"
        item_html = "".join(f'<div class="action-plan-item">{html.escape(item)}</div>' for item in items)
        cards.append(
            f'<div class="action-plan-card {tone}">'
            f'<div class="action-plan-title">{html.escape(title)}</div>'
            f'{item_html}'
            f'</div>'
        )
    st.html(f'<div class="action-plan-grid">{"".join(cards)}</div>')


@st.cache_data(ttl=900, show_spinner=False)
def _download_storage_file_as_b64(bucket: str, path: str) -> str:
    supabase = cached_supabase()
    file_bytes = supabase.storage.from_(bucket).download(path)
    return base64.b64encode(file_bytes).decode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────────────

def _chart_layout(height: int = 285) -> dict:
    return dict(
        height=height,
        margin=dict(t=26, b=28, l=28, r=22),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif', color="#171612", size=13),
    )


def _gauge_chart(score: int) -> go.Figure:
    score = _normalise_score(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "/100", "font": {"size": 42, "color": _score_color(score)}},
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, 25, 50, 75, 100]},
                "bar": {"color": _score_color(score), "thickness": 0.55},
                "bgcolor": "#efede6",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 50], "color": "#f6e9e6"},
                    {"range": [50, 75], "color": "#f5eddd"},
                    {"range": [75, 100], "color": "#e6f0ea"},
                ],
            },
        )
    )
    fig.update_layout(**_chart_layout(270))
    return fig


def _horizontal_score_chart(scores: dict, title: str = "") -> go.Figure:
    clean = [(str(k), _normalise_score(v)) for k, v in (scores or {}).items()]
    if not clean:
        clean = [("No score data", 0)]
    df = pd.DataFrame(clean, columns=["Category", "Score"]).sort_values("Score", ascending=True)
    fig = px.bar(df, x="Score", y="Category", orientation="h", text="Score")
    fig.update_traces(marker_color="#171612", textposition="outside", cliponaxis=False)
    fig.update_layout(
        **_chart_layout(max(250, 48 * len(df) + 80)),
        title=dict(text=title, x=0.02, font=dict(size=16)) if title else None,
        xaxis=dict(range=[0, 108], showgrid=True, gridcolor="#e6e2d9", title=None),
        yaxis=dict(showgrid=False, title=None),
        showlegend=False,
    )
    return fig


def _heading_bar(heading_counts: dict) -> go.Figure:
    heading_counts = heading_counts if isinstance(heading_counts, dict) else {}
    df = pd.DataFrame({
        "Heading": [f"H{i}" for i in range(1, 7)],
        "Count": [int(heading_counts.get(f"h{i}", 0) or 0) for i in range(1, 7)],
    })
    fig = px.bar(df, x="Heading", y="Count", text="Count")
    fig.update_traces(marker_color="#171612", textposition="outside")
    fig.update_layout(
        **_chart_layout(275),
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#e6e2d9", title=None),
        showlegend=False,
    )
    return fig


def _donut_chart(labels: list[str], values: list[int], center_text: str) -> go.Figure:
    if sum(values) <= 0:
        labels = ["No data"]
        values = [1]
    palette = ["#171612", "#b27a16", "#7f7b70", "#c8c3b8"]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.66,
            marker=dict(colors=palette[: len(values)]),
            textinfo="label+percent",
            sort=False,
        )
    )
    fig.add_annotation(text=center_text, x=0.5, y=0.5, showarrow=False, font=dict(size=18, color="#171612"))
    fig.update_layout(**_chart_layout(280), showlegend=False)
    return fig


def _raw_rendered_chart(scraped: dict, report) -> go.Figure:
    labels = ["Words", "H1", "Links", "Schema"]
    raw = [
        int(scraped.get("word_count", 0) or 0),
        int((scraped.get("heading_counts", {}) or {}).get("h1", 0) or 0),
        int(scraped.get("total_links", 0) or 0),
        int(scraped.get("schema_count", 0) or 0),
    ]
    rendered = [
        _rs_int(report, scraped, "rendered_word_count", 0),
        _rs_int(report, scraped, "rendered_h1_count", 0),
        _rs_int(report, scraped, "rendered_total_links", 0),
        _rs_int(report, scraped, "rendered_schema_count", 0),
    ]
    fig = go.Figure()
    fig.add_bar(name="Raw HTML", x=labels, y=raw, marker_color="#7f7b70", text=raw, textposition="outside")
    fig.add_bar(name="Rendered DOM", x=labels, y=rendered, marker_color="#171612", text=rendered, textposition="outside")
    fig.update_layout(
        **_chart_layout(300),
        barmode="group",
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#e6e2d9", title=None),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def _resource_chart(scraped: dict) -> go.Figure:
    labels = ["JavaScript", "CSS", "Images", "Third-party", "Failed"]
    values = [
        int(scraped.get("js_resource_count", 0) or 0),
        int(scraped.get("css_resource_count", 0) or 0),
        int(scraped.get("image_resource_count", 0) or 0),
        int(scraped.get("third_party_resource_count", 0) or 0),
        int(scraped.get("failed_request_count", 0) or 0),
    ]
    fig = px.bar(pd.DataFrame({"Resource": labels, "Count": values}), x="Resource", y="Count", text="Count")
    fig.update_traces(marker_color="#171612", textposition="outside")
    fig.update_layout(
        **_chart_layout(280),
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#e6e2d9", title=None),
        showlegend=False,
    )
    return fig


def _attention_level_chart(elements: list[dict]) -> go.Figure:
    counts = {"High": 0, "Medium": 0, "Low": 0, "Unknown": 0}
    for element in elements or []:
        level = str(element.get("attention_level", "Unknown")).title()
        counts[level if level in counts else "Unknown"] += 1
    df = pd.DataFrame({"Level": list(counts.keys()), "Regions": list(counts.values())})
    fig = px.bar(df, x="Level", y="Regions", text="Regions")
    fig.update_traces(marker_color=["#9c3931", "#9a5a00", "#256b4a", "#7f7b70"], textposition="outside")
    fig.update_layout(
        **_chart_layout(270),
        xaxis=dict(showgrid=False, title=None),
        yaxis=dict(showgrid=True, gridcolor="#e6e2d9", title=None),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Main view
# ─────────────────────────────────────────────────────────────────────────────

def historyView():
    st.html(PAGE_CSS)

    if "active_audit_id" not in st.session_state:
        st.session_state.active_audit_id = None

    supabase = cached_supabase()

    # =========================================================================
    # STATE A — AUDIT REPORT DASHBOARD
    # =========================================================================
    if st.session_state.active_audit_id:
        with st.spinner("Loading audit..."):
            resp = supabase.table("audits").select("*").eq("id", st.session_state.active_audit_id).execute()
            if not resp.data:
                st.error("Audit record not found.")
                return
            rec = resp.data[0]

        try:
            report = SEOAuditReport.model_validate_json(rec["json"])
        except Exception:
            st.error("Stored audit JSON could not be parsed.")
            return

        scraped = _safe_json(rec.get("scraped_data", {}))
        page_url = rec.get("url", "")
        site_title = cached_site_title(page_url) or "SEO Audit Report"
        audit_id = str(st.session_state.active_audit_id)

        pdf_bytes = _cached_audit_pdf(
            audit_id,
            rec["json"],
            json.dumps(scraped),
            page_url,
            site_title,
        )

        nav_col, filler_col = st.columns([1.3, 8.7], vertical_alignment="center")
        with nav_col:
            if st.button(
                "Back to audits",
                type="secondary",
                icon=":material/keyboard_backspace:",
                use_container_width=True,
            ):
                st.session_state.active_audit_id = None
                st.rerun()

        favicon = cached_favicon(page_url)
        favicon_html = (
            f'<img src="{html.escape(favicon, quote=True)}" alt="Site favicon">'
            if favicon
            else "🌐"
        )

        st.html(
            f'''
            <div class="audit-hero">
                <div class="audit-hero-main">
                    <div class="audit-site-mark">{favicon_html}</div>
                    <div class="audit-hero-copy">
                        <h1 class="audit-title">{html.escape(site_title)}</h1>
                        <a class="audit-url" href="{html.escape(page_url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(page_url)}</a>
                        <div class="audit-report-id">Report {html.escape(audit_id)}</div>
                    </div>
                </div>
                <div class="audit-score-panel">
                    <div class="audit-score-number" style="color:{_score_color(report.overall_score)}">{int(report.overall_score)}</div>
                    <div class="audit-score-state">{_score_label(report.overall_score)}</div>
                </div>
            </div>
            '''
        )

        dl_pdf, dl_json, dl_space = st.columns([1.1, 1.1, 7.8], gap="small")
        with dl_pdf:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=f"seotrophy_audit_{audit_id}.pdf",
                mime="application/pdf",
                type="primary",
                icon=":material/download:",
                use_container_width=True,
            )
        with dl_json:
            st.download_button(
                "Download JSON",
                data=report.model_dump_json(indent=2),
                file_name=f"seotrophy_audit_{audit_id}.json",
                mime="application/json",
                type="secondary",
                icon=":material/data_object:",
                use_container_width=True,
            )

        _render_metric_grid([
            ("Overall score", f"{report.overall_score}/100"),
            ("Words", f"{int(scraped.get('word_count', 0) or 0):,}"),
            ("Images", int(scraped.get("total_images", 0) or 0)),
            ("Internal links", int(scraped.get("internal_links", 0) or 0)),
            ("Response", f"{float(scraped.get('response_time_sec', 0) or 0):.3f}s"),
            ("Page size", format_file_size(scraped.get("page_size_kb", 0))),
            ("Indexable", _bool_label(scraped.get("indexable_flag", True))),
            ("JS risk", _rs_value(report, scraped, "js_rendering_risk", "Not checked")),
        ], columns=8)

        tab_ov, tab_md, tab_cs, tab_tc, tab_tr, tab_si, tab_se, tab_js, tab_maps = st.tabs([
            "Overview",
            "Metadata",
            "Content",
            "Technical",
            "Trust",
            "Indexing",
            "Semantics",
            "JavaScript",
            "Visual Maps",
        ])

        # ---------------------------------------------------------------------
        # Overview
        # ---------------------------------------------------------------------
        with tab_ov:
            left, right = st.columns([0.85, 1.45], gap="medium")
            with left:
                st.plotly_chart(_gauge_chart(report.overall_score), use_container_width=True, config={"displayModeBar": False})
            with right:
                st.plotly_chart(
                    _horizontal_score_chart(report.category_scores, "Category performance"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

            _render_heading("Specialist scores")
            _render_score_grid([
                ("Structured data discoverability", report.structured_data_discoverability_score),
                ("Trust and conversion", report.trust_signals_conversion_score),
                ("Content uniqueness", report.content_uniqueness_score),
                ("Search intent match", report.search_intent_match),
                ("Topic coverage", report.topic_coverage_score),
                ("Readability", report.readability_score),
                ("Topical completeness", getattr(report, "topical_completeness", 0)),
                ("Content originality", getattr(report, "content_originality_score", 0)),
            ], columns=4)

            _render_text_panel(
                "Executive summary",
                f"This page scored {report.overall_score}/100. Use the category chart to identify weak systems, then execute the action plan in priority order.",
            )
            _render_heading("Priority action plan")
            _render_action_plan(report.action_item_markdown)

        # ---------------------------------------------------------------------
        # Metadata
        # ---------------------------------------------------------------------
        with tab_md:
            title_col, meta_col = st.columns(2, gap="medium")
            with title_col:
                _render_text_panel("Title tag", report.title_issue, report.suggested_title, "Suggested title")
                _render_metric_grid([
                    ("Length", getattr(report, "title_length_chars", 0)),
                    ("Keyword position", getattr(report, "title_keyword_position", "Missing")),
                    ("Uniqueness", getattr(report, "title_uniqueness", "Low")),
                ], columns=3)
            with meta_col:
                _render_text_panel("Meta description", report.meta_issue, report.suggested_meta, "Suggested description")
                _render_metric_grid([
                    ("Length", getattr(report, "meta_length_chars", 0)),
                    ("Uniqueness", getattr(report, "meta_uniqueness", "Low")),
                    ("CTR potential", getattr(report, "snippet_ctr_potential", 0)),
                ], columns=3)

            _render_heading("Search and social controls")
            _render_status_grid([
                ("Open Graph", scraped.get("open_graph_present")),
                ("Twitter cards", scraped.get("twitter_cards_present")),
                ("Favicon", scraped.get("favicon_present")),
                ("Site name", scraped.get("site_name_present")),
                ("Indexable", scraped.get("indexable_flag")),
                ("HTTPS", scraped.get("is_https")),
                ("Canonical self-reference", scraped.get("canonical_points_to_self")),
                ("Robots blocked", scraped.get("robots_txt_blocks_page")),
            ], columns=4)

            social_col, directive_col = st.columns(2, gap="medium")
            with social_col:
                _render_text_panel("Social preview analysis", report.social_tags_analysis)
                _render_field_grid([
                    ("Open Graph title", scraped.get("open_graph_title", "Missing")),
                    ("Open Graph description", scraped.get("open_graph_description", "Missing")),
                    ("Open Graph image", scraped.get("open_graph_image", "Missing")),
                    ("Twitter image", scraped.get("twitter_card_image", "Missing")),
                ], columns=1)
            with directive_col:
                _render_text_panel("Technical directives", report.indexing_directives_analysis)
                _render_field_grid([
                    ("Canonical URL", scraped.get("canonical_url", "Missing")),
                    ("Canonical status", scraped.get("canonical_status_code", 0)),
                    ("Canonical mismatch", _bool_label(scraped.get("canonical_mismatch"))),
                    ("Multiple canonicals", _bool_label(scraped.get("multiple_canonicals"))),
                    ("robots.txt", _bool_label(scraped.get("robots_txt_present"))),
                    ("Meta robots", scraped.get("meta_robots", "None")),
                    ("Viewport", scraped.get("viewport_string", "Missing")),
                    ("Query strings", _bool_label(scraped.get("has_query_strings"))),
                ], columns=2)

        # ---------------------------------------------------------------------
        # Content
        # ---------------------------------------------------------------------
        with tab_cs:
            _render_metric_grid([
                ("Words", f"{int(scraped.get('word_count', 0) or 0):,}"),
                ("Sentences", scraped.get("total_sentences", 0)),
                ("Average sentence", f"{scraped.get('avg_sentence_length', 0)} words"),
                ("Primary topic", getattr(report, "primary_topic", "Unmapped")),
                ("Search intent", getattr(report, "search_intent_type", "Unmapped")),
                ("Language", getattr(report, "language_detected", "Unknown")),
            ], columns=6)

            content_col, heading_col = st.columns([1.08, 0.92], gap="medium")
            with content_col:
                _render_text_panel("Content depth", report.content_depth_analysis)
                _render_text_panel("Content quality", report.content_quality_analysis)
            with heading_col:
                _render_text_panel("Heading hierarchy", report.heading_hierarchy_analysis)
                st.plotly_chart(_heading_bar(scraped.get("heading_counts", {})), use_container_width=True, config={"displayModeBar": False})

            _render_heading("Content intelligence scores")
            _render_score_grid([
                ("Content uniqueness", report.content_uniqueness_score),
                ("Search intent match", report.search_intent_match),
                ("Topic coverage", report.topic_coverage_score),
                ("Readability", report.readability_score),
                ("Topical completeness", getattr(report, "topical_completeness", 0)),
                ("Content originality", getattr(report, "content_originality_score", 0)),
                ("Source quality", getattr(report, "source_quality_score", 0)),
                ("Heading semantics", 100 if str(getattr(report, "heading_semantics_valid", "Valid")).lower() in {"valid", "yes", "true"} else 40),
            ], columns=4)

            h1_list = scraped.get("h1_contents", [])
            _render_heading("H1 content")
            _render_tags(h1_list, fallback="No H1 detected")

            _render_heading("Body content sample")
            _render_text_panel("Extracted page text", scraped.get("body_context_snippet", "No body snippet stored."))

        # ---------------------------------------------------------------------
        # Technical
        # ---------------------------------------------------------------------
        with tab_tc:
            total_imgs = int(scraped.get("total_images", 0) or 0)
            missing_alt = int(scraped.get("images_missing_alt", 0) or 0)
            covered_alt = max(0, total_imgs - missing_alt)
            internal_links = int(scraped.get("internal_links", 0) or 0)
            external_links = int(scraped.get("external_links", 0) or 0)

            _render_metric_grid([
                ("Images", total_imgs),
                ("Alt coverage", f"{covered_alt}/{total_imgs}" if total_imgs else "0/0"),
                ("Total links", int(scraped.get("total_links", 0) or 0)),
                ("Broken internal", int(scraped.get("broken_internal_links", 0) or 0)),
                ("Response", f"{float(scraped.get('response_time_sec', 0) or 0):.3f}s"),
                ("Page size", format_file_size(scraped.get("page_size_kb", 0))),
                ("HTTPS", _bool_label(scraped.get("is_https"))),
                ("Mobile viewport", _bool_label(scraped.get("has_mobile_viewport"))),
            ], columns=8)

            image_col, link_col = st.columns(2, gap="medium")
            with image_col:
                _render_text_panel("Image accessibility", report.image_alt_analysis)
                st.plotly_chart(
                    _donut_chart(["Alt present", "Alt missing"], [covered_alt, missing_alt], f"{covered_alt}/{total_imgs}" if total_imgs else "0/0"),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                _render_score_grid([
                    ("Alt tag quality", report.image_alt_quality),
                    ("Size optimization", report.image_size_optimization),
                    ("Alt quality score", getattr(report, "alt_quality_score", 0)),
                ], columns=1)
                _render_field_grid([
                    ("Lazy-loaded images", scraped.get("lazy_loading_used", 0)),
                    ("Unoptimized formats", scraped.get("unoptimized_image_formats", 0)),
                ], columns=2)

            with link_col:
                _render_text_panel("Link architecture", report.link_strategy_analysis)
                st.plotly_chart(
                    _donut_chart(["Internal", "External"], [internal_links, external_links], str(internal_links + external_links)),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )
                _render_score_grid([
                    ("Anchor text quality", report.anchor_text_quality),
                    ("Internal relevance", report.internal_link_relevance_score),
                    ("Deep-page discoverability", getattr(report, "deep_page_discoverability", 0)),
                    ("Navigation density", float(getattr(report, "navigation_density", 0) or 0) * 100 if float(getattr(report, "navigation_density", 0) or 0) <= 1 else getattr(report, "navigation_density", 0)),
                ], columns=2)

            url_col, perf_col = st.columns(2, gap="medium")
            with url_col:
                _render_text_panel("URL structure", report.url_structure_analysis)
                _render_field_grid([
                    ("URL length", scraped.get("url_length", 0)),
                    ("Query strings", _bool_label(scraped.get("has_query_strings"))),
                    ("Target URL", page_url),
                    ("Final URL", scraped.get("final_url", page_url)),
                ], columns=1)
            with perf_col:
                _render_text_panel("Security and performance", report.security_performance_analysis)
                _render_field_grid([
                    ("Response time", f"{float(scraped.get('response_time_sec', 0) or 0):.3f}s"),
                    ("Page size", format_file_size(scraped.get("page_size_kb", 0))),
                    ("HTTPS", _bool_label(scraped.get("is_https"))),
                    ("Mobile friendly", _bool_label(scraped.get("mobile_friendly_flag"))),
                ], columns=2)

            _render_text_panel("Media and links detailed analysis", getattr(report, "media_and_links_detailed_analysis", ""))

        # ---------------------------------------------------------------------
        # Trust
        # ---------------------------------------------------------------------
        with tab_tr:
            _render_heading("Visible trust signals")
            _render_status_grid([
                ("About page", scraped.get("has_about_page")),
                ("Contact page", scraped.get("has_contact_page")),
                ("Privacy policy", scraped.get("has_privacy_policy")),
                ("FAQ section", scraped.get("has_faq_section")),
                ("Breadcrumbs", scraped.get("has_breadcrumbs")),
                ("Trust signals", scraped.get("trust_signal_presence")),
                ("Author", getattr(report, "author_present", False)),
                ("Author credentials", getattr(report, "author_credentials_present", False)),
                ("References", getattr(report, "references_present", False)),
                ("CTA", scraped.get("cta_presence")),
                ("ARIA labels", scraped.get("aria_labels_present")),
                ("Form labels", scraped.get("form_labels_present")),
            ], columns=6)

            eeat_col, conversion_col = st.columns(2, gap="medium")
            with eeat_col:
                _render_text_panel("E-E-A-T authority", report.eeat_authority_analysis)
                _render_field_grid([
                    ("Publication date", getattr(report, "publication_date", "Unknown")),
                    ("Last modified", getattr(report, "last_modified_date", "Unknown")),
                    ("Content freshness", getattr(report, "content_freshness", "Unknown")),
                    ("Author credentials", _bool_label(getattr(report, "author_credentials_present", False))),
                ], columns=2)
            with conversion_col:
                _render_text_panel("Conversion trust", report.trust_meta_structural_analysis)
                _render_score_grid([
                    ("Trust and conversion", report.trust_signals_conversion_score),
                    ("Source quality", getattr(report, "source_quality_score", 0)),
                    ("Landmark quality", getattr(report, "landmark_structure_quality", 0)),
                    ("Readability", report.readability_score),
                ], columns=2)

            ux_col, faq_col = st.columns(2, gap="medium")
            with ux_col:
                _render_text_panel("Readability and UX", report.readability_user_experience_analysis)
                _render_field_grid([
                    ("Average sentence", f"{scraped.get('avg_sentence_length', 0)} words"),
                    ("Total sentences", scraped.get("total_sentences", 0)),
                    ("Mobile viewport", _bool_label(scraped.get("has_mobile_viewport"))),
                    ("ARIA landmarks", _bool_label(scraped.get("aria_landmarks_present"))),
                    ("Contrast risk", getattr(report, "contrast_risk_flag", "Low")),
                    ("Viewport", scraped.get("viewport_string", "Missing")),
                ], columns=2)
            with faq_col:
                _render_text_panel("FAQ and breadcrumbs", report.faq_breadcrumbs_analysis)

        # ---------------------------------------------------------------------
        # Indexing and sitemaps
        # ---------------------------------------------------------------------
        with tab_si:
            _render_heading("Indexing health")
            _render_status_grid([
                ("Indexable", scraped.get("indexable_flag")),
                ("Canonical self-reference", scraped.get("canonical_points_to_self")),
                ("Canonical mismatch", scraped.get("canonical_mismatch")),
                ("Robots blocks page", scraped.get("robots_txt_blocks_page")),
                ("Hreflang", scraped.get("hreflang_present")),
                ("Sitemap", scraped.get("sitemap_present")),
                ("Schema", bool(scraped.get("schema_count", 0))),
                ("Breadcrumbs", scraped.get("has_breadcrumbs")),
            ], columns=4)

            schema_col, index_col = st.columns(2, gap="medium")
            with schema_col:
                _render_text_panel("Structured data", report.schema_structured_data_analysis)
                _render_metric_grid([
                    ("Schema objects", scraped.get("schema_count", 0)),
                    ("Validity", scraped.get("schema_validity", "Unknown")),
                    ("Discoverability", report.structured_data_discoverability_score),
                ], columns=3)
                _render_heading("Detected schema types")
                _render_tags(scraped.get("detected_schema_types", []), fallback="No schema types detected")

            with index_col:
                _render_text_panel("Indexing directives", report.indexing_directives_analysis)
                _render_field_grid([
                    ("Canonical URL", scraped.get("canonical_url", "Missing")),
                    ("Canonical status", scraped.get("canonical_status_code", 0)),
                    ("Multiple canonicals", _bool_label(scraped.get("multiple_canonicals"))),
                    ("Canonical chain", scraped.get("canonical_chain_length", 0)),
                    ("robots.txt", _bool_label(scraped.get("robots_txt_present"))),
                    ("Meta robots", scraped.get("meta_robots", "None")),
                    ("X-Robots-Tag", scraped.get("x_robots_tag_header", "None")),
                    ("HTML language", scraped.get("html_lang", "Missing")),
                ], columns=2)

            sitemap_col, hreflang_col = st.columns(2, gap="medium")
            with sitemap_col:
                _render_heading("Sitemap signals")
                sitemap_urls = scraped.get("sitemap_urls") or scraped.get("sitemap_url") or []
                _render_status_grid([
                    ("Sitemap present", scraped.get("sitemap_present")),
                    ("Sitemap index", scraped.get("sitemap_index_present", "Not checked")),
                    ("Page included", scraped.get("sitemap_contains_page", "Not checked")),
                    ("Sitemap status", scraped.get("sitemap_status_code", "Not checked")),
                ], columns=2)
                _render_field_grid([
                    ("Sitemap count", scraped.get("sitemap_count", len(sitemap_urls) if isinstance(sitemap_urls, list) else 1 if sitemap_urls else 0)),
                    ("Sitemap URL", sitemap_urls),
                    ("Last modified", scraped.get("sitemap_lastmod", "Not detected")),
                    ("Discovery source", scraped.get("sitemap_discovery_source", "Not stored")),
                ], columns=1)
            with hreflang_col:
                _render_heading("Hreflang and duplication")
                _render_field_grid([
                    ("Source language", scraped.get("source_language", "Unknown")),
                    ("Hreflang types", scraped.get("hreflang_types", [])),
                    ("Hreflang errors", scraped.get("hreflang_errors", [])),
                    ("Parameter duplicate risk", _bool_label(scraped.get("parameterized_duplicate_risk"))),
                ], columns=1)

        # ---------------------------------------------------------------------
        # Semantics
        # ---------------------------------------------------------------------
        with tab_se:
            _render_metric_grid([
                ("Primary topic", getattr(report, "primary_topic", "Unmapped")),
                ("Search intent", getattr(report, "search_intent_type", "Unmapped")),
                ("Readability grade", getattr(report, "readability_grade_level", "N/A")),
                ("Language", getattr(report, "language_detected", "N/A")),
                ("Freshness", getattr(report, "content_freshness", "Unknown")),
                ("Duplicate risk", getattr(report, "duplicate_content_risk", "Low")),
                ("Keyword stuffing", getattr(report, "keyword_stuffing_risk", "Low")),
                ("Thin content", _bool_label(getattr(report, "thin_content_flag", False))),
            ], columns=8)

            left, right = st.columns([1, 1], gap="medium")
            with left:
                _render_text_panel(
                    "Core semantic profile",
                    f"Primary topic: {getattr(report, 'primary_topic', 'Unmapped')}. Search intent: {getattr(report, 'search_intent_type', 'Unmapped')}. Detected language: {getattr(report, 'language_detected', 'Unknown')}.",
                )
                _render_heading("Secondary topics")
                _render_tags(getattr(report, "secondary_topics", []), fallback="No secondary topics extracted")
                _render_heading("Entity coverage")
                _render_tags(getattr(report, "entity_coverage", []), fallback="No entities extracted")
            with right:
                _render_text_panel("Content quality intelligence", report.content_quality_analysis)
                _render_score_grid([
                    ("Topical completeness", getattr(report, "topical_completeness", 0)),
                    ("Semantic originality", getattr(report, "content_originality_score", 0)),
                    ("Source quality", getattr(report, "source_quality_score", 0)),
                    ("Alt quality", getattr(report, "alt_quality_score", 0)),
                ], columns=2)

            _render_heading("Language, freshness, and authorship")
            _render_field_grid([
                ("Publication date", getattr(report, "publication_date", "Unknown")),
                ("Last modified", getattr(report, "last_modified_date", "Unknown")),
                ("Author present", _bool_label(getattr(report, "author_present", False))),
                ("Author credentials", _bool_label(getattr(report, "author_credentials_present", False))),
                ("References present", _bool_label(getattr(report, "references_present", False))),
                ("Content freshness", getattr(report, "content_freshness", "Unknown")),
            ], columns=3)

        # ---------------------------------------------------------------------
        # JavaScript
        # ---------------------------------------------------------------------
        with tab_js:
            js_checked = _rs_bool(report, scraped, "js_audit_checked", False)
            js_available = _rs_bool(report, scraped, "js_audit_available", False)
            js_risk = _rs_value(report, scraped, "js_rendering_risk", "Not checked")
            js_dependency = _rs_value(report, scraped, "js_content_dependency", "Not checked")
            rendering_gap = _rs_int(report, scraped, "rendering_gap_score", 0)

            if not js_checked:
                _render_text_panel(
                    "JavaScript audit not included",
                    "This report does not contain a browser-rendered JavaScript pass. Run a new exhaustive audit with JavaScript analysis enabled to populate this dashboard.",
                )
            elif not js_available:
                _render_text_panel(
                    "JavaScript audit unavailable",
                    _rs_value(report, scraped, "javascript_rendering_analysis", scraped.get("js_audit_error", "No browser-rendering result was stored.")),
                )
                _render_status_grid([
                    ("Audit checked", js_checked),
                    ("Audit available", js_available),
                    ("Rendering risk", js_risk),
                    ("Stored error", scraped.get("js_audit_error", "Not provided")),
                ], columns=4)
            else:
                _render_metric_grid([
                    ("Rendering gap", f"{rendering_gap}/100"),
                    ("JS risk", js_risk),
                    ("Content dependency", js_dependency),
                    ("Client redirect", _bool_label(_rs_bool(report, scraped, "client_side_redirect_detected", False))),
                    ("JS-added links", _rs_int(report, scraped, "js_added_links", 0)),
                    ("Console errors", _rs_int(report, scraped, "js_console_error_count", 0)),
                    ("Failed requests", _rs_int(report, scraped, "failed_request_count", 0)),
                    ("Total transfer", format_file_size(scraped.get("total_transfer_size_kb", 0))),
                ], columns=8)

                analysis_col, chart_col = st.columns([1, 1.15], gap="medium")
                with analysis_col:
                    _render_text_panel(
                        "JavaScript rendering risk",
                        _rs_value(report, scraped, "javascript_rendering_analysis", "No JavaScript rendering analysis available."),
                    )
                    _render_score_grid([("Rendering gap", rendering_gap)], columns=1)
                with chart_col:
                    st.plotly_chart(_raw_rendered_chart(scraped, report), use_container_width=True, config={"displayModeBar": False})

                metadata_col, fold_col = st.columns(2, gap="medium")
                with metadata_col:
                    _render_text_panel(
                        "Metadata after render",
                        (
                            f"Title changed: {_bool_label(_rs_bool(report, scraped, 'title_changed_after_render', False))}. "
                            f"Meta description changed: {_bool_label(_rs_bool(report, scraped, 'meta_changed_after_render', False))}. "
                            f"Canonical changed: {_bool_label(_rs_bool(report, scraped, 'canonical_changed_after_render', False))}. "
                            f"Robots directive changed: {_bool_label(_rs_bool(report, scraped, 'robots_changed_after_render', False))}."
                        ),
                    )
                    _render_field_grid([
                        ("Rendered title", scraped.get("rendered_title", "Not stored")),
                        ("Rendered meta", scraped.get("rendered_meta_description", "Not stored")),
                        ("Rendered canonical", scraped.get("rendered_canonical_url", "Not stored")),
                        ("Rendered robots", scraped.get("rendered_meta_robots", "Not stored")),
                    ], columns=1)
                with fold_col:
                    _render_text_panel(
                        "Above-the-fold visibility",
                        (
                            f"The first viewport contains {_rs_int(report, scraped, 'above_fold_word_count', 0)} words. "
                            f"H1 visible: {_bool_label(_rs_bool(report, scraped, 'above_fold_h1_visible', False))}. "
                            f"Primary CTA visible: {_bool_label(_rs_bool(report, scraped, 'above_fold_primary_cta_visible', False))}."
                        ),
                    )
                    _render_field_grid([
                        ("Above-fold words", _rs_int(report, scraped, "above_fold_word_count", 0)),
                        ("H1 visible", _bool_label(_rs_bool(report, scraped, "above_fold_h1_visible", False))),
                        ("Primary CTA visible", _bool_label(_rs_bool(report, scraped, "above_fold_primary_cta_visible", False))),
                        ("CTA texts", scraped.get("above_fold_cta_texts", [])),
                    ], columns=2)

                resources_col, diagnostics_col = st.columns([0.9, 1.1], gap="medium")
                with resources_col:
                    st.plotly_chart(_resource_chart(scraped), use_container_width=True, config={"displayModeBar": False})
                with diagnostics_col:
                    _render_field_grid([
                        ("Browser initial URL", scraped.get("browser_initial_url", "Not stored")),
                        ("Browser final URL", scraped.get("browser_final_url", "Not stored")),
                        ("Rendered internal links", scraped.get("rendered_internal_links", "Not stored")),
                        ("Rendered external links", scraped.get("rendered_external_links", "Not stored")),
                        ("Button navigation", scraped.get("button_navigation_count", "Not stored")),
                        ("Resource count", scraped.get("resource_count", "Not stored")),
                        ("Third-party resources", scraped.get("third_party_resource_count", "Not stored")),
                        ("Console warnings", scraped.get("js_console_warning_count", "Not stored")),
                    ], columns=2)

                _render_heading("Above-the-fold text")
                _render_text_panel("Visible first-viewport content", scraped.get("above_fold_text", "No above-the-fold text stored."))

                errors = scraped.get("js_console_errors_preview", []) or []
                warnings = scraped.get("js_console_warnings_preview", []) or []
                failed = scraped.get("failed_requests_preview", []) or []
                err_col, warn_col, fail_col = st.columns(3, gap="medium")
                with err_col:
                    _render_heading("Console errors")
                    _render_tags(errors, fallback="No console errors")
                with warn_col:
                    _render_heading("Console warnings")
                    _render_tags(warnings, fallback="No console warnings")
                with fail_col:
                    _render_heading("Failed requests")
                    _render_tags(failed, fallback="No failed requests")

        # ---------------------------------------------------------------------
        # Visual maps
        # ---------------------------------------------------------------------
        with tab_maps:
            maps = load_audit_visual_maps(supabase, audit_id)

            if not maps:
                _render_text_panel(
                    "No visual maps stored",
                    "Generate a new audit with Page X-Ray enabled to populate attention maps and visual region data.",
                )
            else:
                map_options = []
                for row in maps:
                    label = (
                        f"{row.get('map_type', 'Map')} | "
                        f"{row.get('viewport_width')}×{row.get('viewport_height')} | "
                        f"{'Full page' if row.get('full_page') else 'Viewport'}"
                    )
                    map_options.append((label, row))

                control_col, download_col = st.columns([4, 1.35], gap="medium", vertical_alignment="bottom")
                labels = [label for label, _ in map_options]
                with control_col:
                    selected_label = st.selectbox("Visual map", labels)
                selected_row = dict(map_options[labels.index(selected_label)][1])
                screenshot_b64 = _download_storage_file_as_b64(
                    selected_row.get("screenshot_bucket", "audit-maps"),
                    selected_row["screenshot_path"],
                )
                with download_col:
                    st.download_button(
                        "Download screenshot",
                        data=base64.b64decode(screenshot_b64),
                        file_name=f"visual_map_{audit_id}.png",
                        mime="image/png",
                        icon=":material/download:",
                        type="primary",
                        use_container_width=True,
                    )

                summary = selected_row.get("summary") or {}
                elements = selected_row.get("elements") or []

                _render_metric_grid([
                    ("Regions", summary.get("total_regions", len(elements))),
                    ("High attention", summary.get("high_attention_regions", 0)),
                    ("Medium attention", summary.get("medium_attention_regions", 0)),
                    ("Low attention", summary.get("low_attention_regions", 0)),
                    ("Viewport", f"{selected_row.get('viewport_width')}×{selected_row.get('viewport_height')}"),
                    ("Capture", "Full page" if selected_row.get("full_page") else "Viewport"),
                ], columns=6)

                try:
                    render_data = {
                        "url": selected_row.get("url", page_url),
                        "viewport_width": selected_row.get("viewport_width", 1440),
                        "viewport_height": selected_row.get("viewport_height", 1200),
                        "full_page": selected_row.get("full_page", False),
                        "screenshot_b64": screenshot_b64,
                        "elements": elements,
                    }
                    render_attention_map_html(
                        render_data,
                        width_percent=100,
                        max_visible_height=1100,
                        show_score_badges=True,
                    )
                except Exception as exc:
                    st.error(f"Could not render the visual map: {type(exc).__name__}: {exc}")

                chart_col, table_col = st.columns([0.75, 1.25], gap="medium")
                with chart_col:
                    st.plotly_chart(_attention_level_chart(elements), use_container_width=True, config={"displayModeBar": False})
                with table_col:
                    rows = []
                    for element in sorted(elements, key=lambda x: float(x.get("attention_score", 0) or 0), reverse=True)[:30]:
                        rows.append({
                            "Score": round(float(element.get("attention_score", 0) or 0), 1),
                            "Level": element.get("attention_level", "Unknown"),
                            "Element": element.get("tag", ""),
                            "Content": (element.get("text") or element.get("aria_label") or element.get("href") or "")[:180],
                            "X": round(float(element.get("x", 0) or 0), 1),
                            "Y": round(float(element.get("y", 0) or 0), 1),
                        })
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=310)
                    else:
                        _render_text_panel("Region data", "No attention regions were stored for this map.")


    # =========================================================================
    # STATE B — AUDIT LIST VIEW
    # =========================================================================
    else:
        hdr_col, refresh_col = st.columns([10, 1.5], vertical_alignment="bottom")
        hdr_col.title("Audit History")

        if refresh_col.button("Refresh", type="secondary", use_container_width=True, icon=":material/refresh:"):
            st.cache_data.clear()
            user_audits = get_user_audits_new(st.session_state.uid)
        else:
            user_audits = None

        st.html(
            "<p class='small-muted' style='margin-top:-10px; margin-bottom:2rem;'>View, manage, and export your previous technical SEO reports.</p>"
        )

        if user_audits is None:
            with st.spinner("Loading..."):
                user_audits = get_user_audits(st.session_state.uid)

        if not user_audits:
            st.info("No audits found. Run your first forensic analysis to get started.")
            return

        active_audits = [a for a in user_audits if not a.get("is_archived")]
        archived_audits = [a for a in user_audits if a.get("is_archived")]

        def render_audit_card(audit, is_vault=False):
            url = audit.get("url", "")
            audit_id = audit.get("id")
            title = cached_site_title(url) or "Untitled Domain"
            fav = cached_favicon(url)
            created_at = dt.datetime.fromisoformat(audit["created_at"])

            score = 0
            try:
                report_data = json.loads(audit.get("json", "{}"))
                score = int(report_data.get("overall_score", 0))
            except Exception:
                pass

            score_color = _score_color(score)

            with st.container(border=True):
                st.space("small")
                sp1, c_fav, c_info, c_score, c_acts, sp2 = st.columns([0.01, 1, 5.5, 1.5, 3, 0.3], gap="medium", vertical_alignment="center")

                with c_fav:
                    if fav:
                        st.image(fav, use_container_width=True)
                    else:
                        st.html("🌐")

                with c_info:
                    st.html(
                        f"<div style='font-size:1.2rem;font-weight:600;color:#0f172a;margin-bottom:2px;'>{html.escape(title)}</div>"
                    )
                    st.caption(f":gray[[{url}]({url})]")
                    c1, c2 = st.columns([1, 2], gap="small")
                    c1.html(
                        f"<div style='font-size:0.75rem;color:#64748b;margin-top:4px;'>{created_at.strftime('%b %d, %Y')} · {time_ago(audit['created_at'])}</div>"
                    )
                    if is_vault:
                        c2.badge("Archived", color="yellow", icon=":material/stars:", width="stretch")

                with c_score:
                    st.html(
                        f"""
                        <div class="score-badge" style="border-color: {score_color}40; background: {score_color}10; color: {score_color}; width: 75px; margin: 0 auto;">
                            <div class="score-num">{score}</div>
                            <div class="score-lbl">Score</div>
                        </div>
                        """
                    )

                with c_acts:
                    if st.button("View Report", type="primary", icon=":material/assessment:", use_container_width=True, key=f"open_{audit_id}"):
                        st.session_state.active_audit_id = audit_id
                        st.rerun()

                    c_pdf, c_a = st.columns(2, gap="small")
                    pdf_key = f"pdf_bytes_{audit_id}"
                    pdf_slot = c_pdf.empty()

                    if pdf_key in st.session_state:
                        pdf_slot.download_button(
                            label="Confirm",
                            data=st.session_state[pdf_key],
                            file_name=f"seo_audit_{audit_id}.pdf",
                            mime="application/pdf",
                            type="primary",
                            icon=":material/download:",
                            use_container_width=True,
                            key=f"dl_{audit_id}",
                            on_click=_reset_pdf_download,
                            args=(audit_id,),
                        )
                    elif pdf_slot.button(
                        "PDF",
                        type="secondary",
                        icon=":material/download:",
                        use_container_width=True,
                        key=f"dl_btn_{audit_id}",
                    ):
                        with st.spinner("Generating PDF..."):
                            try:
                                resp = (
                                    supabase.table("audits")
                                    .select("json, scraped_data, url")
                                    .eq("id", audit_id)
                                    .limit(1)
                                    .execute()
                                )
                                if not resp.data:
                                    st.error("Audit record not found.")
                                else:
                                    rec = resp.data[0]
                                    st.session_state[pdf_key] = _cached_audit_pdf(
                                        str(audit_id),
                                        rec["json"],
                                        json.dumps(_safe_json(rec.get("scraped_data", {}))),
                                        rec.get("url", url),
                                        title,
                                    )
                                    pdf_slot.download_button(
                                        label="Confirm",
                                        data=st.session_state[pdf_key],
                                        file_name=f"seo_audit_{audit_id}.pdf",
                                        mime="application/pdf",
                                        type="secondary",
                                        icon=":material/download:",
                                        use_container_width=True,
                                        key=f"dl_{audit_id}",
                                        on_click=_reset_pdf_download,
                                        args=(audit_id,),
                                    )
                                    st.rerun()
                            except Exception:
                                st.error("Could not generate PDF for this audit.")

                    with c_a.popover("Actions", use_container_width=True):
                        if not is_vault:
                            if st.button("Archive", icon=":material/stars:", use_container_width=True, key=f"arch_{audit_id}"):
                                supabase.table("audits").update({"is_archived": True}).eq("id", audit_id).execute()
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            if st.button("Restore", icon=":material/unarchive:", use_container_width=True, key=f"unarch_{audit_id}"):
                                supabase.table("audits").update({"is_archived": False}).eq("id", audit_id).execute()
                                st.cache_data.clear()
                                st.rerun()

                        if st.button("Delete", icon=":material/delete:", use_container_width=True, key=f"del_{audit_id}"):
                            with st.spinner("Deleting..."):
                                supabase.table("audits").delete().eq("id", audit_id).execute()
                                st.cache_data.clear()
                            st.rerun()
                st.space("small")

        st.html('''<style>
                        button[data-baseweb="tab"] {
                        font-size: 24px;
                        margin: 0;
                        width: 100%;
                        }
                        </style>
                ''')

        t1, t2 = st.tabs(["All Audits", "Archived"])

        with t1:
            if not active_audits:
                st.info("No active audits found.")
            else:
                for audit in active_audits:
                    render_audit_card(audit, is_vault=False)

        with t2:
            if not archived_audits:
                st.info("Your archive vault is empty.")
            else:
                for audit in archived_audits:
                    render_audit_card(audit, is_vault=True)


