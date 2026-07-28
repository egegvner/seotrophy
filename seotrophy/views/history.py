import base64
import datetime as dt
import html
import json
import logging
from typing import Any

import pandas as pd
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
    load_audit_visual_maps,
    render_attention_map_html,
    time_ago,
)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Flat dashboard theme
# ─────────────────────────────────────────────────────────────────────────────

PAGE_CSS = """
<style>
:root {
    --dash-bg: #f7f6f2;
    --dash-panel: #ffffff;
    --dash-panel-soft: #f1efe8;
    --dash-text: #171611;
    --dash-muted: #686458;
    --dash-border: #dcd8ce;
    --dash-border-strong: #bcb6a9;
    --dash-accent: #c9962f;
    --dash-accent-soft: #f4ead1;
    --dash-good: #18794e;
    --dash-good-soft: #e6f2ec;
    --dash-warn: #9a6700;
    --dash-warn-soft: #f7edcf;
    --dash-bad: #b42318;
    --dash-bad-soft: #fbe9e7;
    --dash-neutral: #54504a;
}

.stApp {
    background: var(--dash-bg);
}

header[data-testid="stHeader"] {
    background: var(--dash-bg);
}

.block-container {
    max-width: 1500px !important;
    padding-top: 1.6rem !important;
    padding-bottom: 4rem !important;
}

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    color: var(--dash-text);
}

::selection {
    background: var(--dash-text);
    color: #ffffff;
}

.dashboard-header {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1.4rem;
    margin: 0.8rem 0 1rem;
}

.dashboard-header-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1.4rem;
    align-items: center;
}

.dashboard-site-row {
    display: flex;
    align-items: center;
    gap: 0.9rem;
}

.dashboard-favicon {
    width: 48px;
    height: 48px;
    border: 1px solid var(--dash-border);
    background: var(--dash-panel-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}

.dashboard-favicon img {
    width: 30px;
    height: 30px;
    object-fit: contain;
}

.dashboard-title {
    margin: 0;
    font-size: clamp(1.8rem, 3vw, 2.8rem);
    line-height: 1.05;
    letter-spacing: -0.045em;
    font-weight: 800;
}

.dashboard-url {
    display: block;
    margin-top: 0.55rem;
    color: var(--dash-muted);
    font-size: 1rem;
    overflow-wrap: anywhere;
    text-decoration: none;
}

.dashboard-score {
    min-width: 170px;
    border-left: 5px solid var(--dash-accent);
    background: var(--dash-panel-soft);
    padding: 1rem 1.2rem;
    text-align: right;
}

.dashboard-score-value {
    font-size: 3rem;
    line-height: 0.95;
    font-weight: 850;
    letter-spacing: -0.06em;
}

.dashboard-score-label {
    margin-top: 0.45rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--dash-muted);
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
    gap: 0.7rem;
    margin-bottom: 1rem;
}

.metric-tile {
    min-height: 104px;
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 0.95rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.metric-tile-label {
    color: var(--dash-muted);
    font-size: 0.88rem;
    font-weight: 700;
    line-height: 1.25;
}

.metric-tile-value {
    margin-top: 0.65rem;
    color: var(--dash-text);
    font-size: 1.55rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.035em;
    overflow-wrap: anywhere;
}

.metric-tile.good { border-top: 4px solid var(--dash-good); }
.metric-tile.warn { border-top: 4px solid var(--dash-warn); }
.metric-tile.bad { border-top: 4px solid var(--dash-bad); }
.metric-tile.accent { border-top: 4px solid var(--dash-accent); }
.metric-tile.neutral { border-top: 4px solid var(--dash-neutral); }

.section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    margin: 0.2rem 0 0.75rem;
    padding-bottom: 0.65rem;
    border-bottom: 2px solid var(--dash-text);
}

.section-heading h2,
.section-heading h3 {
    margin: 0;
    color: var(--dash-text);
    font-size: 1.25rem;
    line-height: 1.2;
    font-weight: 800;
    letter-spacing: -0.025em;
}

.panel {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1.1rem;
    margin-bottom: 0.8rem;
}

.panel-title {
    margin: 0 0 0.75rem;
    font-size: 1.08rem;
    line-height: 1.25;
    font-weight: 800;
    color: var(--dash-text);
}

.panel-body {
    color: var(--dash-text);
    font-size: 1rem;
    line-height: 1.65;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.panel.recommendation {
    border-left: 5px solid var(--dash-accent);
    background: var(--dash-accent-soft);
}

.panel.critical {
    border-left: 5px solid var(--dash-bad);
    background: var(--dash-bad-soft);
}

.panel.success {
    border-left: 5px solid var(--dash-good);
    background: var(--dash-good-soft);
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.8rem;
}

.detail-item {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 0.9rem;
    min-height: 88px;
}

.detail-label {
    color: var(--dash-muted);
    font-size: 0.88rem;
    font-weight: 700;
    line-height: 1.25;
}

.detail-value {
    margin-top: 0.45rem;
    color: var(--dash-text);
    font-size: 1.03rem;
    font-weight: 750;
    line-height: 1.4;
    overflow-wrap: anywhere;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.85rem;
}

.status-card {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 0.9rem;
    min-height: 90px;
}

.status-card.good { border-left: 5px solid var(--dash-good); }
.status-card.warn { border-left: 5px solid var(--dash-warn); }
.status-card.bad { border-left: 5px solid var(--dash-bad); }
.status-card.neutral { border-left: 5px solid var(--dash-neutral); }

.status-label {
    color: var(--dash-muted);
    font-size: 0.88rem;
    font-weight: 700;
}

.status-value {
    margin-top: 0.45rem;
    color: var(--dash-text);
    font-size: 1.08rem;
    line-height: 1.35;
    font-weight: 800;
    overflow-wrap: anywhere;
}

.score-list {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1rem;
    margin-bottom: 0.8rem;
}

.score-row {
    display: grid;
    grid-template-columns: minmax(170px, 1fr) 3fr 62px;
    gap: 0.75rem;
    align-items: center;
    margin-bottom: 0.85rem;
}

.score-row:last-child { margin-bottom: 0; }
.score-name { font-size: 0.95rem; font-weight: 700; color: var(--dash-text); }
.score-track { height: 14px; background: var(--dash-panel-soft); border: 1px solid var(--dash-border); }
.score-fill { height: 100%; background: var(--dash-text); }
.score-fill.good { background: var(--dash-good); }
.score-fill.warn { background: var(--dash-warn); }
.score-fill.bad { background: var(--dash-bad); }
.score-number { text-align: right; font-size: 1rem; font-weight: 800; }

.chip-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-bottom: 0.8rem;
}

.data-chip {
    border: 1px solid var(--dash-border-strong);
    background: var(--dash-panel);
    padding: 0.6rem 0.8rem;
    color: var(--dash-text);
    font-size: 0.95rem;
    font-weight: 700;
    line-height: 1.25;
}

.snippet-preview {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}

.snippet-url {
    color: var(--dash-good);
    font-size: 0.95rem;
    overflow-wrap: anywhere;
}

.snippet-title {
    color: #1a0dab;
    font-size: 1.35rem;
    line-height: 1.3;
    margin: 0.45rem 0;
    font-weight: 600;
}

.snippet-description {
    color: #3c4043;
    font-size: 1rem;
    line-height: 1.55;
}

.text-preview {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel-soft);
    padding: 1rem;
    color: var(--dash-text);
    font-size: 1rem;
    line-height: 1.65;
    white-space: pre-wrap;
    max-height: 360px;
    overflow-y: auto;
    overflow-wrap: anywhere;
}

.action-stack {
    display: grid;
    gap: 0.65rem;
}

.action-card {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 0.95rem;
}

.action-card.high { border-left: 6px solid var(--dash-bad); }
.action-card.medium { border-left: 6px solid var(--dash-warn); }
.action-card.low { border-left: 6px solid var(--dash-good); }
.action-title { font-size: 1rem; font-weight: 850; margin-bottom: 0.55rem; }
.action-item { font-size: 0.98rem; line-height: 1.5; padding: 0.35rem 0; border-top: 1px solid var(--dash-border); }
.action-item:first-of-type { border-top: 0; }

.empty-state {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1.4rem;
    color: var(--dash-muted);
    font-size: 1rem;
    line-height: 1.55;
}

.audit-list-card {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 1rem;
    margin-bottom: 0.75rem;
}

.audit-list-title {
    color: var(--dash-text);
    font-size: 1.18rem;
    font-weight: 800;
    line-height: 1.25;
}

.audit-list-url {
    color: var(--dash-muted);
    font-size: 0.95rem;
    overflow-wrap: anywhere;
}


button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--dash-text) !important;
}

[data-baseweb="tab-highlight"] {
    background-color: var(--dash-accent) !important;
    height: 4px !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--dash-border);
}

[data-testid="stMetric"] {
    border: 1px solid var(--dash-border);
    background: var(--dash-panel);
    padding: 0.9rem;
}

[data-testid="stMetricLabel"] p {
    font-size: 0.9rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricValue"] {
    font-size: 1.7rem !important;
    font-weight: 800 !important;
}

[data-testid="stProgress"] p {
    font-size: 0.96rem !important;
    font-weight: 700 !important;
}

.stButton > button,
.stDownloadButton > button {
    min-height: 44px;
    border-radius: 0 !important;
    font-weight: 750 !important;
}

hr { border-color: var(--dash-border); }

@media (max-width: 1200px) {
    .metric-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
    .block-container { padding-top: 1rem !important; }
    .dashboard-header-grid { grid-template-columns: 1fr; }
    .dashboard-score { text-align: left; width: 100%; }
    .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .detail-grid, .status-grid { grid-template-columns: 1fr; }
    .score-row { grid-template-columns: 1fr 2fr 48px; }
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Data and display helpers
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
def _cached_audit_pdf(
    audit_id: str,
    report_json: str,
    scraped_json: str,
    page_url: str,
    site_title: str,
) -> bytes:
    report = SEOAuditReport.model_validate_json(report_json)
    scraped = _safe_json(scraped_json)
    return _build_audit_pdf(
        report=report,
        scraped=scraped,
        page_url=page_url,
        site_title=site_title,
        audit_id=audit_id,
    )


@st.cache_data(ttl=900, show_spinner=False)
def _download_storage_file_as_b64(bucket: str, path: str) -> str:
    supabase = cached_supabase()
    file_bytes = supabase.storage.from_(bucket).download(path)
    return base64.b64encode(file_bytes).decode("utf-8")


def _reset_pdf_download(audit_id) -> None:
    st.session_state.pop(f"pdf_bytes_{audit_id}", None)
    st.session_state.pop(f"pdf_error_{audit_id}", None)


def _safe_display(value: Any, fallback: str = "Not detected") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value.strip() or fallback
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else fallback
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False) if value else fallback
    return str(value)


def _safe_html(value: Any, fallback: str = "Not detected") -> str:
    return html.escape(_safe_display(value, fallback))


def _bool_label(value: Any) -> str:
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1", "present", "available", "valid"}:
            return "Yes"
        if lowered in {"false", "no", "0", "missing", "unavailable", "invalid"}:
            return "No"
    return "Yes" if bool(value) else "No"


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
        return value.strip().lower() in {"true", "yes", "1", "present", "available"}
    return bool(value)


def _score_color(score: int | float) -> str:
    try:
        score = float(score)
    except Exception:
        score = 0
    if score >= 75:
        return "#18794e"
    if score >= 50:
        return "#9a6700"
    return "#b42318"


def _score_label(score: int | float) -> str:
    try:
        score = float(score)
    except Exception:
        score = 0
    if score >= 75:
        return "Strong"
    if score >= 50:
        return "Needs work"
    return "Critical"


def _state_from_score(score: int | float) -> str:
    try:
        score = float(score)
    except Exception:
        score = 0
    if score >= 75:
        return "good"
    if score >= 50:
        return "warn"
    return "bad"


def _state_from_bool(value: Any, positive: bool = True) -> str:
    state = bool(value)
    if isinstance(value, str):
        state = value.strip().lower() in {"true", "yes", "1", "present", "available", "valid"}
    success = state if positive else not state
    return "good" if success else "bad"


def format_file_size(size_kb: float) -> str:
    try:
        size_kb = float(size_kb)
    except Exception:
        size_kb = 0
    if size_kb < 1000:
        return f"{size_kb:.1f} KB"
    return f"{size_kb / 1000:.2f} MB"


def _section_heading(title: str) -> None:
    st.html(f'<div class="section-heading"><h2>{html.escape(title)}</h2></div>')


def _panel(title: str, body: Any, kind: str = "") -> None:
    body_text = _safe_display(body, "No analysis available.")
    st.html(
        f'''
        <div class="panel {html.escape(kind)}">
            <div class="panel-title">{html.escape(title)}</div>
            <div class="panel-body">{html.escape(body_text)}</div>
        </div>
        '''
    )


def _metric_grid(rows: list[tuple[str, Any, str]]) -> None:
    cards = []
    for label, value, state in rows:
        cards.append(
            f'''
            <div class="metric-tile {html.escape(state or 'neutral')}">
                <div class="metric-tile-label">{html.escape(str(label))}</div>
                <div class="metric-tile-value">{_safe_html(value)}</div>
            </div>
            '''
        )
    st.html(f'<div class="metric-grid">{"".join(cards)}</div>')


def _detail_grid(rows: list[tuple[str, Any]], columns: int = 2) -> None:
    items = []
    for label, value in rows:
        items.append(
            f'''
            <div class="detail-item">
                <div class="detail-label">{html.escape(str(label))}</div>
                <div class="detail-value">{_safe_html(value)}</div>
            </div>
            '''
        )
    st.html(
        f'<div class="detail-grid" style="grid-template-columns:repeat({max(1, columns)},minmax(0,1fr));">'
        f'{"".join(items)}</div>'
    )


def _status_grid(rows: list[tuple[str, Any, str]], columns: int = 3) -> None:
    cards = []
    for label, value, state in rows:
        cards.append(
            f'''
            <div class="status-card {html.escape(state or 'neutral')}">
                <div class="status-label">{html.escape(str(label))}</div>
                <div class="status-value">{_safe_html(value)}</div>
            </div>
            '''
        )
    st.html(
        f'<div class="status-grid" style="grid-template-columns:repeat({max(1, columns)},minmax(0,1fr));">'
        f'{"".join(cards)}</div>'
    )


def _score_bars(rows: list[tuple[str, Any]]) -> None:
    blocks = []
    for label, raw in rows:
        try:
            score = max(0, min(100, float(raw)))
            shown = f"{score:.0f}"
        except Exception:
            score = 0
            shown = _safe_display(raw, "0")
        state = _state_from_score(score)
        blocks.append(
            f'''
            <div class="score-row">
                <div class="score-name">{html.escape(str(label))}</div>
                <div class="score-track"><div class="score-fill {state}" style="width:{score:.1f}%"></div></div>
                <div class="score-number">{html.escape(shown)}</div>
            </div>
            '''
        )
    st.html(f'<div class="score-list">{"".join(blocks)}</div>')


def _chips(items: list[Any], empty_message: str = "None detected") -> None:
    clean = [str(item).strip() for item in (items or []) if str(item).strip()]
    if not clean:
        st.html(f'<div class="empty-state">{html.escape(empty_message)}</div>')
        return
    chips = "".join(f'<span class="data-chip">{html.escape(item)}</span>' for item in clean)
    st.html(f'<div class="chip-list">{chips}</div>')


def _text_preview(text: Any, empty_message: str = "No text captured") -> None:
    content = _safe_display(text, empty_message)
    st.html(f'<div class="text-preview">{html.escape(content)}</div>')


def _dataframe(rows: list[tuple[str, Any]], *, height: int | None = None) -> None:
    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    df["Value"] = df["Value"].map(lambda value: _safe_display(value))
    kwargs = {
        "hide_index": True,
        "use_container_width": True,
    }
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


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
        st.html('<div class="empty-state">No action items were generated.</div>')
        return

    cards = []
    for title, items in sections:
        title_lower = title.lower()
        tone = "high" if "high" in title_lower else "medium" if "medium" in title_lower else "low"
        item_html = "".join(f'<div class="action-item">{html.escape(item)}</div>' for item in items)
        cards.append(
            f'<div class="action-card {tone}"><div class="action-title">{html.escape(title)}</div>{item_html}</div>'
        )
    st.html(f'<div class="action-stack">{"".join(cards)}</div>')


def _gauge_chart(score: int | float, title: str = "Overall SEO health") -> go.Figure:
    try:
        score = max(0, min(100, float(score)))
    except Exception:
        score = 0
    color = _score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 50, "color": color}, "suffix": "/100"},
            title={"text": title, "font": {"size": 18, "color": "#171611"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0, "tickfont": {"size": 11}},
                "bar": {"color": color, "thickness": 0.7},
                "bgcolor": "#f1efe8",
                "bordercolor": "#dcd8ce",
                "borderwidth": 1,
                "steps": [
                    {"range": [0, 50], "color": "#fbe9e7"},
                    {"range": [50, 75], "color": "#f7edcf"},
                    {"range": [75, 100], "color": "#e6f2ec"},
                ],
            },
        )
    )
    fig.update_layout(
        height=285,
        margin=dict(t=50, b=20, l=25, r=25),
        paper_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#171611"),
    )
    return fig


def _horizontal_score_chart(rows: list[tuple[str, Any]], title: str = "") -> go.Figure:
    labels: list[str] = []
    values: list[float] = []
    colors: list[str] = []
    for label, value in rows:
        try:
            numeric = max(0, min(100, float(value)))
        except Exception:
            numeric = 0
        labels.append(str(label))
        values.append(numeric)
        colors.append(_score_color(numeric))

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            text=[f"{v:.0f}" for v in values],
            textposition="inside",
            insidetextanchor="end",
            marker_color=colors,
            hovertemplate="%{y}: %{x:.0f}/100<extra></extra>",
        )
    )
    fig.update_layout(
        title={"text": title, "font": {"size": 18}} if title else None,
        height=max(270, 52 * len(labels) + 70),
        margin=dict(t=45 if title else 20, b=35, l=20, r=20),
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#e5e1d8", zeroline=False),
        yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        font=dict(family="Arial, sans-serif", color="#171611"),
    )
    return fig


def _donut_chart(labels: list[str], values: list[float], center: str = "") -> go.Figure:
    safe_values = [max(0, float(v or 0)) for v in values]
    if sum(safe_values) <= 0:
        safe_values = [1 for _ in values]
    palette = ["#171611", "#c9962f", "#7c7669", "#18794e", "#b42318", "#9a6700"]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=safe_values,
            hole=0.62,
            marker={"colors": palette[: len(labels)], "line": {"color": "#ffffff", "width": 2}},
            textinfo="label+value",
            hovertemplate="%{label}: %{value}<extra></extra>",
        )
    )
    if center:
        fig.add_annotation(text=center, x=0.5, y=0.5, showarrow=False, font={"size": 18, "color": "#171611"})
    fig.update_layout(
        height=290,
        margin=dict(t=20, b=20, l=20, r=20),
        showlegend=False,
        paper_bgcolor="#ffffff",
        font=dict(family="Arial, sans-serif", color="#171611", size=13),
    )
    return fig


def _heading_chart(heading_counts: dict) -> go.Figure:
    counts = heading_counts if isinstance(heading_counts, dict) else {}
    labels = [f"H{i}" for i in range(1, 7)]
    values = [int(counts.get(f"h{i}", 0) or 0) for i in range(1, 7)]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#c9962f" if i == 0 else "#171611" for i in range(6)],
            text=values,
            textposition="outside",
            hovertemplate="%{x}: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        height=290,
        margin=dict(t=25, b=35, l=30, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#e5e1d8", zeroline=False),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        showlegend=False,
        font=dict(family="Arial, sans-serif", color="#171611", size=13),
    )
    return fig


def _comparison_chart(labels: list[str], raw: list[float], rendered: list[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Raw HTML", x=labels, y=raw, marker_color="#7c7669"))
    fig.add_trace(go.Bar(name="Rendered DOM", x=labels, y=rendered, marker_color="#c9962f"))
    fig.update_layout(
        barmode="group",
        height=320,
        margin=dict(t=30, b=50, l=35, r=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#e5e1d8", zeroline=False),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend=dict(orientation="h", y=1.08, x=0),
        font=dict(family="Arial, sans-serif", color="#171611", size=13),
    )
    return fig


def _risk_distribution(category_scores: dict) -> tuple[list[str], list[int]]:
    buckets = {"Strong": 0, "Needs work": 0, "Critical": 0}
    for value in (category_scores or {}).values():
        try:
            score = float(value)
        except Exception:
            score = 0
        if score >= 75:
            buckets["Strong"] += 1
        elif score >= 50:
            buckets["Needs work"] += 1
        else:
            buckets["Critical"] += 1
    return list(buckets.keys()), list(buckets.values())


def _render_report_header(report, page_url: str, site_title: str, audit_id: str) -> None:
    fav_url = cached_favicon(page_url)
    favicon_html = (
        f'<img src="{html.escape(fav_url, quote=True)}" alt="Site favicon">'
        if fav_url
        else '<span style="font-size:1.4rem;">◎</span>'
    )
    st.html(
        f'''
        <div class="dashboard-header">
            <div class="dashboard-header-grid">
                <div class="dashboard-site-row">
                    <div class="dashboard-favicon">{favicon_html}</div>
                    <div>
                        <h1 class="dashboard-title">{html.escape(site_title)}</h1>
                        <a class="dashboard-url" href="{html.escape(page_url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(page_url)}</a>
                    </div>
                </div>
                <div class="dashboard-score">
                    <div class="dashboard-score-value">{int(report.overall_score)}</div>
                    <div class="dashboard-score-label">SEO score · {_score_label(report.overall_score)}</div>
                </div>
            </div>
        </div>
        '''
    )


def _render_top_metrics(report, scraped: dict) -> None:
    overall = int(getattr(report, "overall_score", 0) or 0)
    response = float(scraped.get("response_time_sec", 0) or 0)
    page_size = float(scraped.get("page_size_kb", 0) or 0)
    indexable = bool(scraped.get("indexable_flag", True))
    js_risk = _rs_value(report, scraped, "js_rendering_risk", "Not checked")
    js_state = "neutral"
    if isinstance(js_risk, str):
        risk_lower = js_risk.lower()
        if "low" in risk_lower:
            js_state = "good"
        elif "medium" in risk_lower:
            js_state = "warn"
        elif "high" in risk_lower:
            js_state = "bad"

    _metric_grid([
        ("Overall", f"{overall}/100", _state_from_score(overall)),
        ("Indexable", _bool_label(indexable), _state_from_bool(indexable)),
        ("Words", f"{int(scraped.get('word_count', 0) or 0):,}", "accent"),
        ("Links", int(scraped.get("total_links", 0) or 0), "neutral"),
        ("Images", int(scraped.get("total_images", 0) or 0), "neutral"),
        ("Response", f"{response:.2f}s", "good" if response <= 1 else "warn" if response <= 2.5 else "bad"),
        ("Page size", format_file_size(page_size), "good" if page_size <= 1500 else "warn" if page_size <= 3000 else "bad"),
        ("JS risk", js_risk, js_state),
    ])


def _render_overview_tab(report, scraped: dict) -> None:
    _section_heading("Audit command center")
    left, middle, right = st.columns([1, 1.25, 1.15], gap="medium")

    with left:
        st.plotly_chart(_gauge_chart(report.overall_score), use_container_width=True, config={"displayModeBar": False})
        labels, values = _risk_distribution(report.category_scores)
        st.plotly_chart(_donut_chart(labels, values, "Categories"), use_container_width=True, config={"displayModeBar": False})

    with middle:
        category_rows = [(str(k).replace("_", " ").title(), v) for k, v in (report.category_scores or {}).items()]
        st.plotly_chart(
            _horizontal_score_chart(category_rows, "Category performance"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        _section_heading("Specialist scores")
        _score_bars([
            ("Structured data", getattr(report, "structured_data_discoverability_score", 0)),
            ("Trust and conversion", getattr(report, "trust_signals_conversion_score", 0)),
            ("Content uniqueness", getattr(report, "content_uniqueness_score", 0)),
            ("Search intent match", getattr(report, "search_intent_match", 0)),
            ("Topic coverage", getattr(report, "topic_coverage_score", 0)),
            ("Readability", getattr(report, "readability_score", 0)),
            ("Topical completeness", getattr(report, "topical_completeness", 0)),
            ("Content originality", getattr(report, "content_originality_score", 0)),
        ])

    with right:
        _panel(
            "Executive summary",
            f"The page scored {report.overall_score}/100. Review the critical categories first, then resolve the highest-priority actions below.",
            "recommendation",
        )
        _section_heading("Priority action plan")
        _render_action_plan(getattr(report, "action_item_markdown", ""))


def _render_metadata_tab(report, scraped: dict, page_url: str) -> None:
    _section_heading("Search result presentation")
    title_text = getattr(report, "suggested_title", "") or scraped.get("title", "") or "Untitled page"
    meta_text = getattr(report, "suggested_meta", "") or scraped.get("meta_description", "") or "No meta description detected."
    st.html(
        f'''
        <div class="snippet-preview">
            <div class="snippet-url">{html.escape(page_url)}</div>
            <div class="snippet-title">{html.escape(str(title_text))}</div>
            <div class="snippet-description">{html.escape(str(meta_text))}</div>
        </div>
        '''
    )

    title_col, meta_col = st.columns(2, gap="medium")
    with title_col:
        _panel("Title tag analysis", getattr(report, "title_issue", ""))
        _detail_grid([
            ("Title length", getattr(report, "title_length_chars", 0)),
            ("Keyword position", getattr(report, "title_keyword_position", "Missing")),
            ("Uniqueness", getattr(report, "title_uniqueness", "Unknown")),
        ], columns=3)
        _panel("Recommended title", getattr(report, "suggested_title", ""), "recommendation")

    with meta_col:
        _panel("Meta description analysis", getattr(report, "meta_issue", ""))
        _detail_grid([
            ("Meta length", getattr(report, "meta_length_chars", 0)),
            ("Uniqueness", getattr(report, "meta_uniqueness", "Unknown")),
            ("CTR potential", getattr(report, "snippet_ctr_potential", 0)),
        ], columns=3)
        _panel("Recommended description", getattr(report, "suggested_meta", ""), "recommendation")

    social_col, directive_col = st.columns(2, gap="medium")
    with social_col:
        _section_heading("Social preview readiness")
        _status_grid([
            ("Open Graph", _bool_label(scraped.get("open_graph_present")), _state_from_bool(scraped.get("open_graph_present"))),
            ("Twitter cards", _bool_label(scraped.get("twitter_cards_present")), _state_from_bool(scraped.get("twitter_cards_present"))),
            ("Favicon", _bool_label(scraped.get("favicon_present")), _state_from_bool(scraped.get("favicon_present"))),
            ("Site name", _bool_label(scraped.get("site_name_present")), _state_from_bool(scraped.get("site_name_present"))),
        ], columns=2)
        _panel("Social metadata analysis", getattr(report, "social_tags_analysis", ""))
        _dataframe([
            ("OG title", scraped.get("open_graph_title", "")),
            ("OG description", scraped.get("open_graph_description", "")),
            ("OG image", scraped.get("open_graph_image", "")),
            ("Twitter image", scraped.get("twitter_card_image", "")),
        ], height=250)

    with directive_col:
        _section_heading("Page directives")
        _status_grid([
            ("Indexable", _bool_label(scraped.get("indexable_flag")), _state_from_bool(scraped.get("indexable_flag"))),
            ("HTTPS", _bool_label(scraped.get("is_https")), _state_from_bool(scraped.get("is_https"))),
            ("Self canonical", _bool_label(scraped.get("canonical_points_to_self")), _state_from_bool(scraped.get("canonical_points_to_self"))),
            ("Robots blocked", _bool_label(scraped.get("robots_txt_blocks_page")), _state_from_bool(scraped.get("robots_txt_blocks_page"), positive=False)),
        ], columns=2)
        _panel("Directive analysis", getattr(report, "indexing_directives_analysis", ""))
        _dataframe([
            ("Canonical URL", scraped.get("canonical_url", "Missing")),
            ("Canonical status", scraped.get("canonical_status_code", 0)),
            ("Canonical mismatch", _bool_label(scraped.get("canonical_mismatch"))),
            ("Multiple canonicals", _bool_label(scraped.get("multiple_canonicals"))),
            ("Robots.txt", _bool_label(scraped.get("robots_txt_present"))),
            ("Meta robots", scraped.get("meta_robots", "None")),
            ("Viewport", scraped.get("viewport_string", "Missing")),
            ("Query strings", _bool_label(scraped.get("has_query_strings"))),
        ], height=320)


def _render_content_tab(report, scraped: dict) -> None:
    _section_heading("Content intelligence")
    _metric_grid([
        ("Words", f"{int(scraped.get('word_count', 0) or 0):,}", "accent"),
        ("Sentences", int(scraped.get("total_sentences", 0) or 0), "neutral"),
        ("Average sentence", f"{scraped.get('avg_sentence_length', 0)} words", "neutral"),
        ("Language", getattr(report, "language_detected", "Unknown"), "neutral"),
        ("Intent", getattr(report, "search_intent_type", "Unknown"), "accent"),
        ("Topic", getattr(report, "primary_topic", "Unknown"), "accent"),
        ("Thin content", _bool_label(getattr(report, "thin_content_flag", False)), _state_from_bool(getattr(report, "thin_content_flag", False), positive=False)),
        ("Readability", getattr(report, "readability_score", 0), _state_from_score(getattr(report, "readability_score", 0))),
    ])

    content_col, heading_col = st.columns([1.15, 1], gap="medium")
    with content_col:
        _panel("Content depth analysis", getattr(report, "content_depth_analysis", ""))
        _panel("Content quality analysis", getattr(report, "content_quality_analysis", ""))
        _section_heading("Extracted body preview")
        _text_preview(scraped.get("body_context_snippet", ""))

    with heading_col:
        _panel("Heading hierarchy analysis", getattr(report, "heading_hierarchy_analysis", ""))
        st.plotly_chart(_heading_chart(scraped.get("heading_counts", {})), use_container_width=True, config={"displayModeBar": False})
        h1_list = scraped.get("h1_contents", []) or []
        _section_heading("Detected H1 headings")
        _chips(h1_list, "No H1 heading was detected")

    score_left, score_right = st.columns(2, gap="medium")
    with score_left:
        _section_heading("Semantic performance")
        _score_bars([
            ("Content uniqueness", getattr(report, "content_uniqueness_score", 0)),
            ("Search intent match", getattr(report, "search_intent_match", 0)),
            ("Topic coverage", getattr(report, "topic_coverage_score", 0)),
            ("Readability", getattr(report, "readability_score", 0)),
        ])
    with score_right:
        _section_heading("Extraction quality")
        _score_bars([
            ("Topical completeness", getattr(report, "topical_completeness", 0)),
            ("Content originality", getattr(report, "content_originality_score", 0)),
            ("Source quality", getattr(report, "source_quality_score", 0)),
            ("Alt quality", getattr(report, "alt_quality_score", 0)),
        ])


def _render_technical_tab(report, scraped: dict, page_url: str) -> None:
    total_imgs = int(scraped.get("total_images", 0) or 0)
    missing_alt = int(scraped.get("images_missing_alt", 0) or 0)
    covered_alt = max(0, total_imgs - missing_alt)
    internal_links = int(scraped.get("internal_links", 0) or 0)
    external_links = int(scraped.get("external_links", 0) or 0)

    image_col, link_col = st.columns(2, gap="medium")
    with image_col:
        _section_heading("Image accessibility")
        st.plotly_chart(
            _donut_chart(["Alt present", "Alt missing"], [covered_alt, missing_alt], f"{covered_alt}/{total_imgs}"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        _status_grid([
            ("Total images", total_imgs, "neutral"),
            ("Missing alt", missing_alt, "good" if missing_alt == 0 else "bad"),
            ("Lazy loaded", scraped.get("lazy_loading_used", 0), "neutral"),
            ("Old formats", scraped.get("unoptimized_image_formats", 0), "good" if not scraped.get("unoptimized_image_formats", 0) else "warn"),
        ], columns=2)
        _score_bars([
            ("Alt tag quality", getattr(report, "image_alt_quality", 0)),
            ("Size optimization", getattr(report, "image_size_optimization", 0)),
            ("Alt quality score", getattr(report, "alt_quality_score", 0)),
        ])
        _panel("Image analysis", getattr(report, "image_alt_analysis", ""))

    with link_col:
        _section_heading("Link architecture")
        st.plotly_chart(
            _donut_chart(["Internal", "External"], [internal_links, external_links], f"{internal_links + external_links}"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        _status_grid([
            ("Total links", scraped.get("total_links", 0), "neutral"),
            ("Internal", internal_links, "accent"),
            ("External", external_links, "neutral"),
            ("Broken internal", scraped.get("broken_internal_links", 0), "good" if not scraped.get("broken_internal_links", 0) else "bad"),
        ], columns=2)
        _score_bars([
            ("Anchor text quality", getattr(report, "anchor_text_quality", 0)),
            ("Internal relevance", getattr(report, "internal_link_relevance_score", 0)),
            ("Deep discoverability", getattr(report, "deep_page_discoverability", 0)),
            ("Navigation density", getattr(report, "navigation_density", 0)),
        ])
        _panel("Link strategy analysis", getattr(report, "link_strategy_analysis", ""))

    url_col, perf_col = st.columns(2, gap="medium")
    with url_col:
        _section_heading("URL structure")
        _panel("URL analysis", getattr(report, "url_structure_analysis", ""))
        _dataframe([
            ("Target URL", page_url),
            ("Final URL", scraped.get("final_url", page_url)),
            ("URL length", scraped.get("url_length", 0)),
            ("Query strings", _bool_label(scraped.get("has_query_strings"))),
        ], height=220)

    with perf_col:
        _section_heading("Security and performance")
        response = float(scraped.get("response_time_sec", 0) or 0)
        page_size = float(scraped.get("page_size_kb", 0) or 0)
        _status_grid([
            ("Response", f"{response:.3f}s", "good" if response <= 1 else "warn" if response <= 2.5 else "bad"),
            ("Page size", format_file_size(page_size), "good" if page_size <= 1500 else "warn" if page_size <= 3000 else "bad"),
            ("HTTPS", _bool_label(scraped.get("is_https")), _state_from_bool(scraped.get("is_https"))),
            ("Mobile viewport", _bool_label(scraped.get("has_mobile_viewport")), _state_from_bool(scraped.get("has_mobile_viewport"))),
        ], columns=2)
        _panel("Performance analysis", getattr(report, "security_performance_analysis", ""))

    _section_heading("Media and links assessment")
    _panel("Detailed analysis", getattr(report, "media_and_links_detailed_analysis", ""))


def _render_trust_tab(report, scraped: dict) -> None:
    _section_heading("Trust signal matrix")
    _status_grid([
        ("About page", _bool_label(scraped.get("has_about_page")), _state_from_bool(scraped.get("has_about_page"))),
        ("Contact page", _bool_label(scraped.get("has_contact_page")), _state_from_bool(scraped.get("has_contact_page"))),
        ("Privacy policy", _bool_label(scraped.get("has_privacy_policy")), _state_from_bool(scraped.get("has_privacy_policy"))),
        ("FAQ section", _bool_label(scraped.get("has_faq_section")), _state_from_bool(scraped.get("has_faq_section"))),
        ("Breadcrumbs", _bool_label(scraped.get("has_breadcrumbs")), _state_from_bool(scraped.get("has_breadcrumbs"))),
        ("Author", _bool_label(getattr(report, "author_present", False)), _state_from_bool(getattr(report, "author_present", False))),
        ("Credentials", _bool_label(getattr(report, "author_credentials_present", False)), _state_from_bool(getattr(report, "author_credentials_present", False))),
        ("References", _bool_label(getattr(report, "references_present", False)), _state_from_bool(getattr(report, "references_present", False))),
        ("CTA", _bool_label(scraped.get("cta_presence")), _state_from_bool(scraped.get("cta_presence"))),
    ], columns=3)

    authority_col, conversion_col = st.columns(2, gap="medium")
    with authority_col:
        _section_heading("E-E-A-T authority")
        _panel("Authority analysis", getattr(report, "eeat_authority_analysis", ""))
        _dataframe([
            ("Publication date", getattr(report, "publication_date", "Unknown")),
            ("Last modified", getattr(report, "last_modified_date", "Unknown")),
            ("Content freshness", getattr(report, "content_freshness", "Unknown")),
            ("Author credentials", _bool_label(getattr(report, "author_credentials_present", False))),
        ], height=220)

    with conversion_col:
        _section_heading("Conversion and UX")
        _score_bars([
            ("Trust and conversion", getattr(report, "trust_signals_conversion_score", 0)),
            ("Source quality", getattr(report, "source_quality_score", 0)),
            ("Landmark quality", getattr(report, "landmark_structure_quality", 0)),
            ("Readability", getattr(report, "readability_score", 0)),
        ])
        _panel("Trust structure analysis", getattr(report, "trust_meta_structural_analysis", ""))
        _panel("Readability and UX", getattr(report, "readability_user_experience_analysis", ""))

    access_col, faq_col = st.columns(2, gap="medium")
    with access_col:
        _section_heading("Accessibility readiness")
        _status_grid([
            ("Mobile friendly", _bool_label(scraped.get("mobile_friendly_flag")), _state_from_bool(scraped.get("mobile_friendly_flag"))),
            ("ARIA labels", _bool_label(scraped.get("aria_labels_present")), _state_from_bool(scraped.get("aria_labels_present"))),
            ("Form labels", _bool_label(scraped.get("form_labels_present")), _state_from_bool(scraped.get("form_labels_present"))),
            ("ARIA landmarks", _bool_label(scraped.get("aria_landmarks_present")), _state_from_bool(scraped.get("aria_landmarks_present"))),
            ("Contrast risk", getattr(report, "contrast_risk_flag", "Unknown"), "bad" if str(getattr(report, "contrast_risk_flag", "")).lower() == "high" else "warn"),
            ("Viewport", _bool_label(scraped.get("has_mobile_viewport")), _state_from_bool(scraped.get("has_mobile_viewport"))),
        ], columns=2)
    with faq_col:
        _section_heading("FAQ and breadcrumbs")
        _panel("Structural analysis", getattr(report, "faq_breadcrumbs_analysis", ""))


def _render_indexing_tab(report, scraped: dict) -> None:
    _section_heading("Indexing control plane")
    _status_grid([
        ("Indexable", _bool_label(scraped.get("indexable_flag")), _state_from_bool(scraped.get("indexable_flag"))),
        ("Self canonical", _bool_label(scraped.get("canonical_points_to_self")), _state_from_bool(scraped.get("canonical_points_to_self"))),
        ("Canonical mismatch", _bool_label(scraped.get("canonical_mismatch")), _state_from_bool(scraped.get("canonical_mismatch"), positive=False)),
        ("Robots block", _bool_label(scraped.get("robots_txt_blocks_page")), _state_from_bool(scraped.get("robots_txt_blocks_page"), positive=False)),
        ("Hreflang", _bool_label(scraped.get("hreflang_present")), _state_from_bool(scraped.get("hreflang_present"))),
        ("Sitemap", _bool_label(scraped.get("sitemap_present")), _state_from_bool(scraped.get("sitemap_present"))),
    ], columns=3)

    schema_col, directive_col = st.columns([1, 1.2], gap="medium")
    with schema_col:
        _section_heading("Structured data")
        _score_bars([
            ("Discoverability", getattr(report, "structured_data_discoverability_score", 0)),
        ])
        _status_grid([
            ("Schema objects", scraped.get("schema_count", 0), "neutral"),
            ("Schema validity", scraped.get("schema_validity", "Unknown"), "good" if str(scraped.get("schema_validity", "")).lower() in {"valid", "yes", "true"} else "warn"),
            ("Breadcrumbs", _bool_label(scraped.get("has_breadcrumbs")), _state_from_bool(scraped.get("has_breadcrumbs"))),
        ], columns=3)
        _panel("Structured data analysis", getattr(report, "schema_structured_data_analysis", ""))
        _section_heading("Detected schema types")
        _chips(scraped.get("detected_schema_types", []) or [], "No schema types detected")

    with directive_col:
        _section_heading("Canonical, robots and hreflang")
        _panel("Indexing analysis", getattr(report, "indexing_directives_analysis", ""))
        _dataframe([
            ("Canonical URL", scraped.get("canonical_url", "Missing")),
            ("Multiple canonicals", _bool_label(scraped.get("multiple_canonicals"))),
            ("Canonical chain length", scraped.get("canonical_chain_length", 0)),
            ("Canonical status", scraped.get("canonical_status_code", 0)),
            ("robots.txt present", _bool_label(scraped.get("robots_txt_present"))),
            ("Meta robots", scraped.get("meta_robots", "None")),
            ("X-Robots-Tag", scraped.get("x_robots_tag_header", "None")),
            ("HTML language", scraped.get("html_lang", "Missing")),
            ("Source language", scraped.get("source_language", "Unknown")),
            ("Hreflang types", scraped.get("hreflang_types", [])),
            ("Hreflang errors", scraped.get("hreflang_errors", [])),
            ("Parameter duplication risk", _bool_label(scraped.get("parameterized_duplicate_risk"))),
        ], height=445)


def _render_semantics_tab(report, scraped: dict) -> None:
    _section_heading("Semantic profile")
    _metric_grid([
        ("Primary topic", getattr(report, "primary_topic", "Unmapped"), "accent"),
        ("Search intent", getattr(report, "search_intent_type", "Unmapped"), "accent"),
        ("Language", getattr(report, "language_detected", "Unknown"), "neutral"),
        ("Readability grade", getattr(report, "readability_grade_level", "Unknown"), "neutral"),
        ("Freshness", getattr(report, "content_freshness", "Unknown"), "neutral"),
        ("Duplicate risk", getattr(report, "duplicate_content_risk", "Unknown"), "warn"),
        ("Keyword stuffing", getattr(report, "keyword_stuffing_risk", "Unknown"), "warn"),
        ("Thin content", _bool_label(getattr(report, "thin_content_flag", False)), _state_from_bool(getattr(report, "thin_content_flag", False), positive=False)),
    ])

    score_col, analysis_col = st.columns([1, 1.15], gap="medium")
    with score_col:
        _section_heading("Content quality scores")
        _score_bars([
            ("Topical completeness", getattr(report, "topical_completeness", 0)),
            ("Content originality", getattr(report, "content_originality_score", 0)),
            ("Source quality", getattr(report, "source_quality_score", 0)),
            ("Alt quality", getattr(report, "alt_quality_score", 0)),
            ("Search intent match", getattr(report, "search_intent_match", 0)),
            ("Topic coverage", getattr(report, "topic_coverage_score", 0)),
        ])
        _dataframe([
            ("Publication date", getattr(report, "publication_date", "Unknown")),
            ("Last modified", getattr(report, "last_modified_date", "Unknown")),
            ("Author present", _bool_label(getattr(report, "author_present", False))),
            ("Credentials", _bool_label(getattr(report, "author_credentials_present", False))),
            ("References", _bool_label(getattr(report, "references_present", False))),
        ], height=260)

    with analysis_col:
        _section_heading("Content quality analysis")
        _panel("Semantic assessment", getattr(report, "content_quality_analysis", ""))
        _panel(
            "Profile summary",
            f"Primary topic: {getattr(report, 'primary_topic', 'Unmapped')}. Search intent: {getattr(report, 'search_intent_type', 'Unmapped')}. Detected language: {getattr(report, 'language_detected', 'Unknown')}.",
            "recommendation",
        )

    topics_col, entities_col = st.columns(2, gap="medium")
    with topics_col:
        _section_heading("Secondary topics")
        _chips(getattr(report, "secondary_topics", []) or [], "No secondary topics were extracted")
    with entities_col:
        _section_heading("Detected entities")
        _chips(getattr(report, "entity_coverage", []) or [], "No semantic entities were extracted")


def _render_js_tab(report, scraped: dict) -> None:
    js_checked = _rs_bool(report, scraped, "js_audit_checked", False)
    js_available = _rs_bool(report, scraped, "js_audit_available", False)
    js_risk = _rs_value(report, scraped, "js_rendering_risk", "Not checked")
    js_dependency = _rs_value(report, scraped, "js_content_dependency", "Not checked")
    rendering_gap = _rs_int(report, scraped, "rendering_gap_score", 0)

    if not js_checked:
        _panel(
            "JavaScript audit not included",
            "This report does not contain a browser-rendered audit. Run an exhaustive audit with the JavaScript pass enabled to populate this dashboard.",
            "recommendation",
        )
        return

    if not js_available:
        _panel(
            "JavaScript audit unavailable",
            _rs_value(report, scraped, "javascript_rendering_analysis", scraped.get("js_audit_error", "No usable browser result was stored.")),
            "critical",
        )
        _status_grid([
            ("Audit checked", _bool_label(js_checked), _state_from_bool(js_checked)),
            ("Result available", _bool_label(js_available), _state_from_bool(js_available)),
            ("Rendering risk", js_risk, "warn"),
            ("Error", scraped.get("js_audit_error", "Not provided"), "bad"),
        ], columns=2)
        return

    _section_heading("JavaScript rendering dashboard")
    _metric_grid([
        ("Rendering gap", f"{rendering_gap}/100", _state_from_score(100 - rendering_gap)),
        ("Rendering risk", js_risk, "warn" if "medium" in str(js_risk).lower() else "bad" if "high" in str(js_risk).lower() else "good"),
        ("Content dependency", js_dependency, "warn"),
        ("Client redirect", _bool_label(_rs_bool(report, scraped, "client_side_redirect_detected", False)), _state_from_bool(_rs_bool(report, scraped, "client_side_redirect_detected", False), positive=False)),
        ("Console errors", _rs_int(report, scraped, "js_console_error_count", 0), "good" if _rs_int(report, scraped, "js_console_error_count", 0) == 0 else "bad"),
        ("Failed requests", _rs_int(report, scraped, "failed_request_count", 0), "good" if _rs_int(report, scraped, "failed_request_count", 0) == 0 else "bad"),
        ("JS-added links", _rs_int(report, scraped, "js_added_links", 0), "neutral"),
        ("Rendered schemas", _rs_int(report, scraped, "rendered_schema_count", 0), "neutral"),
    ])

    analysis_col, compare_col = st.columns([1, 1.2], gap="medium")
    with analysis_col:
        _panel("Rendering analysis", _rs_value(report, scraped, "javascript_rendering_analysis", "No analysis available."))
        st.plotly_chart(_gauge_chart(100 - rendering_gap, "Rendered parity"), use_container_width=True, config={"displayModeBar": False})
    with compare_col:
        st.plotly_chart(
            _comparison_chart(
                ["Words", "Links", "H1", "Schema"],
                [
                    int(scraped.get("word_count", 0) or 0),
                    int(scraped.get("total_links", 0) or 0),
                    int((scraped.get("heading_counts", {}) or {}).get("h1", 0) or 0),
                    int(scraped.get("schema_count", 0) or 0),
                ],
                [
                    _rs_int(report, scraped, "rendered_word_count", 0),
                    _rs_int(report, scraped, "rendered_total_links", 0),
                    _rs_int(report, scraped, "rendered_h1_count", 0),
                    _rs_int(report, scraped, "rendered_schema_count", 0),
                ],
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        _detail_grid([
            ("After-scroll words", _rs_int(report, scraped, "after_scroll_word_count", 0)),
            ("Scroll-revealed delta", _rs_int(report, scraped, "scroll_revealed_word_delta", 0)),
            ("Rendered word delta", _rs_int(report, scraped, "rendered_word_delta", 0)),
            ("Schema added by JS", _bool_label(_rs_bool(report, scraped, "schema_added_by_js", False))),
        ], columns=2)

    metadata_col, fold_col = st.columns(2, gap="medium")
    with metadata_col:
        _section_heading("Metadata after render")
        _status_grid([
            ("Title changed", _bool_label(_rs_bool(report, scraped, "title_changed_after_render", False)), _state_from_bool(_rs_bool(report, scraped, "title_changed_after_render", False), positive=False)),
            ("Meta changed", _bool_label(_rs_bool(report, scraped, "meta_changed_after_render", False)), _state_from_bool(_rs_bool(report, scraped, "meta_changed_after_render", False), positive=False)),
            ("Canonical changed", _bool_label(_rs_bool(report, scraped, "canonical_changed_after_render", False)), _state_from_bool(_rs_bool(report, scraped, "canonical_changed_after_render", False), positive=False)),
            ("Robots changed", _bool_label(_rs_bool(report, scraped, "robots_changed_after_render", False)), _state_from_bool(_rs_bool(report, scraped, "robots_changed_after_render", False), positive=False)),
        ], columns=2)
        _dataframe([
            ("Rendered title", scraped.get("rendered_title", "Not stored")),
            ("Rendered meta", scraped.get("rendered_meta_description", "Not stored")),
            ("Rendered canonical", scraped.get("rendered_canonical_url", "Not stored")),
            ("Rendered robots", scraped.get("rendered_meta_robots", "Not stored")),
        ], height=230)

    with fold_col:
        _section_heading("Above-the-fold visibility")
        _status_grid([
            ("Visible words", _rs_int(report, scraped, "above_fold_word_count", 0), "neutral"),
            ("H1 visible", _bool_label(_rs_bool(report, scraped, "above_fold_h1_visible", False)), _state_from_bool(_rs_bool(report, scraped, "above_fold_h1_visible", False))),
            ("Primary CTA", _bool_label(_rs_bool(report, scraped, "above_fold_primary_cta_visible", False)), _state_from_bool(_rs_bool(report, scraped, "above_fold_primary_cta_visible", False))),
            ("CTA text", scraped.get("above_fold_cta_texts", []), "neutral"),
        ], columns=2)
        _text_preview(scraped.get("above_fold_text", ""), "No above-the-fold text was stored")

    diag_col, resources_col = st.columns([1.15, 0.85], gap="medium")
    with diag_col:
        _section_heading("Browser diagnostics")
        _dataframe([
            ("Initial URL", scraped.get("browser_initial_url", "Not stored")),
            ("Final URL", scraped.get("browser_final_url", "Not stored")),
            ("Rendered internal links", scraped.get("rendered_internal_links", "Not stored")),
            ("Rendered external links", scraped.get("rendered_external_links", "Not stored")),
            ("Button navigation", scraped.get("button_navigation_count", "Not stored")),
            ("Total transfer", format_file_size(float(scraped.get("total_transfer_size_kb", 0) or 0))),
            ("Third-party resources", scraped.get("third_party_resource_count", "Not stored")),
            ("Console warnings", scraped.get("js_console_warning_count", "Not stored")),
        ], height=350)
    with resources_col:
        _section_heading("Resource mix")
        st.plotly_chart(
            _donut_chart(
                ["JavaScript", "CSS", "Images", "Other"],
                [
                    int(scraped.get("js_resource_count", 0) or 0),
                    int(scraped.get("css_resource_count", 0) or 0),
                    int(scraped.get("image_resource_count", 0) or 0),
                    max(0, int(scraped.get("resource_count", 0) or 0) - int(scraped.get("js_resource_count", 0) or 0) - int(scraped.get("css_resource_count", 0) or 0) - int(scraped.get("image_resource_count", 0) or 0)),
                ],
                "Resources",
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    errors = scraped.get("js_console_errors_preview", []) or []
    warnings = scraped.get("js_console_warnings_preview", []) or []
    failed = scraped.get("failed_requests_preview", []) or []
    err_col, warn_col, fail_col = st.columns(3, gap="medium")
    with err_col:
        _section_heading("Console errors")
        if errors:
            st.dataframe(pd.DataFrame({"Error": errors}), hide_index=True, use_container_width=True, height=260)
        else:
            st.html('<div class="empty-state">No console errors stored.</div>')
    with warn_col:
        _section_heading("Console warnings")
        if warnings:
            st.dataframe(pd.DataFrame({"Warning": warnings}), hide_index=True, use_container_width=True, height=260)
        else:
            st.html('<div class="empty-state">No console warnings stored.</div>')
    with fail_col:
        _section_heading("Failed requests")
        if failed:
            st.dataframe(pd.DataFrame({"URL": failed}), hide_index=True, use_container_width=True, height=260)
        else:
            st.html('<div class="empty-state">No failed requests stored.</div>')


def _render_maps_tab(supabase, audit_id: str, page_url: str) -> None:
    _section_heading("Visual site maps")
    maps = load_audit_visual_maps(supabase, audit_id)

    if not maps:
        st.html(
            '<div class="empty-state">No visual map artifacts were stored for this audit. Run a new audit with Page X-Ray enabled.</div>'
        )
        return

    map_options: list[tuple[str, dict]] = []
    for row in maps:
        label = (
            f"{str(row.get('map_type', 'map')).replace('_', ' ').title()} · "
            f"{row.get('viewport_width', '?')}×{row.get('viewport_height', '?')} · "
            f"{'Full page' if row.get('full_page') else 'Viewport'}"
        )
        map_options.append((label, row))

    control_col, download_col = st.columns([4, 1], gap="medium", vertical_alignment="bottom")
    labels = [label for label, _ in map_options]
    selected_label = control_col.selectbox("Visual artifact", labels, label_visibility="visible")
    selected_row = dict(map_options[labels.index(selected_label)][1])

    screenshot_b64 = _download_storage_file_as_b64(
        selected_row.get("screenshot_bucket", "audit-maps"),
        selected_row["screenshot_path"],
    )
    download_col.download_button(
        "Download image",
        data=base64.b64decode(screenshot_b64),
        file_name=f"site_map_{audit_id}.png",
        mime="image/png",
        type="primary",
        use_container_width=True,
    )

    summary = selected_row.get("summary") or {}
    elements = selected_row.get("elements") or []
    high_count = int(summary.get("high_attention_regions", 0) or 0)
    medium_count = int(summary.get("medium_attention_regions", 0) or 0)
    low_count = int(summary.get("low_attention_regions", 0) or 0)

    _metric_grid([
        ("Regions", summary.get("total_regions", len(elements)), "accent"),
        ("High attention", high_count, "bad"),
        ("Medium attention", medium_count, "warn"),
        ("Low attention", low_count, "good"),
        ("Viewport width", selected_row.get("viewport_width", "Unknown"), "neutral"),
        ("Viewport height", selected_row.get("viewport_height", "Unknown"), "neutral"),
        ("Capture", "Full page" if selected_row.get("full_page") else "Viewport", "neutral"),
        ("Map type", selected_row.get("map_type", "Map"), "accent"),
    ])

    chart_col, table_col = st.columns([0.75, 1.25], gap="medium")
    with chart_col:
        st.plotly_chart(
            _donut_chart(["High", "Medium", "Low"], [high_count, medium_count, low_count], "Attention"),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        _panel(
            "Map interpretation",
            "Attention levels are simulated from screenshot structure and DOM regions. They do not represent real visitor tracking.",
            "recommendation",
        )

    rows = []
    for element in sorted(elements, key=lambda item: float(item.get("attention_score", 0) or 0), reverse=True)[:30]:
        rows.append({
            "Score": round(float(element.get("attention_score", 0) or 0), 1),
            "Level": element.get("attention_level", "Unknown"),
            "Element": element.get("tag", ""),
            "Content": (element.get("text") or element.get("aria_label") or element.get("href") or "")[:180],
            "X": round(float(element.get("x", 0) or 0), 1),
            "Y": round(float(element.get("y", 0) or 0), 1),
            "Width": round(float(element.get("width", 0) or 0), 1),
            "Height": round(float(element.get("height", 0) or 0), 1),
        })

    with table_col:
        _section_heading("Highest-attention regions")
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=390)
        else:
            st.html('<div class="empty-state">No mapped regions were stored.</div>')

    _section_heading("Interactive visual map")
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
        st.error(f"Could not load stored visual map screenshot: {type(exc).__name__}: {exc}")


def _render_audit_report(supabase, rec: dict) -> None:
    try:
        report = SEOAuditReport.model_validate_json(rec["json"])
    except Exception:
        st.error("Stored audit JSON could not be parsed.")
        return

    scraped = _safe_json(rec.get("scraped_data", {}))
    page_url = rec.get("url", "")
    audit_id = str(st.session_state.active_audit_id)
    site_title = cached_site_title(page_url) or "SEO Audit Report"

    nav_col, action_col = st.columns([5, 2.4], gap="medium", vertical_alignment="center")
    with nav_col:
        if st.button("Back to audits", icon=":material/arrow_back:", use_container_width=False):
            st.session_state.active_audit_id = None
            st.rerun()

    pdf_key = f"pdf_bytes_{audit_id}"
    pdf_error_key = f"pdf_error_{audit_id}"

    with action_col:
        pdf_col, json_col = st.columns(2, gap="small")

        if pdf_key in st.session_state:
            pdf_col.download_button(
                "Download PDF",
                data=st.session_state[pdf_key],
                file_name=f"seotrophy_audit_{audit_id}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key=f"download_report_pdf_{audit_id}",
                on_click=_reset_pdf_download,
                args=(audit_id,),
            )
        elif pdf_col.button(
            "Prepare PDF",
            type="primary",
            use_container_width=True,
            key=f"prepare_report_pdf_{audit_id}",
        ):
            st.session_state.pop(pdf_error_key, None)
            try:
                with st.spinner("Preparing PDF..."):
                    st.session_state[pdf_key] = _cached_audit_pdf(
                        audit_id=audit_id,
                        report_json=rec["json"],
                        scraped_json=json.dumps(scraped),
                        page_url=page_url,
                        site_title=site_title,
                    )
                st.rerun()
            except Exception:
                logger.exception("Could not generate PDF for audit %s", audit_id)
                st.session_state[pdf_error_key] = (
                    "PDF generation is temporarily unavailable. "
                    "The audit dashboard and JSON export are still available."
                )
                st.rerun()

        json_col.download_button(
            "Download JSON",
            data=report.model_dump_json(indent=2),
            file_name=f"seotrophy_audit_{audit_id}.json",
            mime="application/json",
            use_container_width=True,
        )

    if pdf_error_key in st.session_state:
        st.warning(st.session_state[pdf_error_key])

    _render_report_header(report, page_url, site_title, audit_id)
    _render_top_metrics(report, scraped)

    tabs = st.tabs([
        "Overview",
        "Metadata",
        "Content",
        "Technical",
        "Trust",
        "Indexing",
        "Semantics",
        "JavaScript",
        "Site Maps",
    ], width="stretch")

    with tabs[0]:
        _render_overview_tab(report, scraped)
    with tabs[1]:
        _render_metadata_tab(report, scraped, page_url)
    with tabs[2]:
        _render_content_tab(report, scraped)
    with tabs[3]:
        _render_technical_tab(report, scraped, page_url)
    with tabs[4]:
        _render_trust_tab(report, scraped)
    with tabs[5]:
        _render_indexing_tab(report, scraped)
    with tabs[6]:
        _render_semantics_tab(report, scraped)
    with tabs[7]:
        _render_js_tab(report, scraped)
    with tabs[8]:
        _render_maps_tab(supabase, audit_id, page_url)


def _render_audit_list(supabase) -> None:
    header_col, refresh_col = st.columns([8, 1.4], vertical_alignment="bottom")
    header_col.title("Audit History")

    if refresh_col.button("Refresh", use_container_width=True, icon=":material/refresh:"):
        st.cache_data.clear()
        user_audits = get_user_audits_new(st.session_state.uid)
    else:
        user_audits = None

    if user_audits is None:
        with st.spinner("Loading audits..."):
            user_audits = get_user_audits(st.session_state.uid)

    if not user_audits:
        st.info("No audits found. Run your first audit to create a report.")
        return

    active_audits = [audit for audit in user_audits if not audit.get("is_archived")]
    archived_audits = [audit for audit in user_audits if audit.get("is_archived")]

    def render_audit_card(audit: dict, archived: bool = False) -> None:
        url = audit.get("url", "")
        audit_id = audit.get("id")
        title = cached_site_title(url) or "Untitled domain"
        fav = cached_favicon(url)
        created_at = dt.datetime.fromisoformat(audit["created_at"])

        try:
            report_data = json.loads(audit.get("json", "{}"))
            score = int(report_data.get("overall_score", 0))
        except Exception:
            score = 0

        with st.container(border=True):
            fav_col, info_col, score_col, action_col = st.columns(
                [0.7, 4.6, 1, 2.4],
                gap="medium",
                vertical_alignment="center",
            )
            with fav_col:
                if fav:
                    st.image(fav, width=46)
                else:
                    st.markdown("## ◎")

            with info_col:
                st.html(
                    f'''
                    <div class="audit-list-title">{html.escape(title)}</div>
                    <div class="audit-list-url">{html.escape(url)}</div>
                    <div style="margin-top:.45rem;font-size:.95rem;color:#686458;">
                        {created_at.strftime('%b %d, %Y')} · {html.escape(time_ago(audit['created_at']))}
                        {' · Archived' if archived else ''}
                    </div>
                    '''
                )

            with score_col:
                _status_grid([("Score", score, _state_from_score(score))], columns=1)

            with action_col:
                if st.button(
                    "View report",
                    type="primary",
                    use_container_width=True,
                    key=f"open_{audit_id}",
                ):
                    st.session_state.active_audit_id = audit_id
                    st.rerun()

                pdf_col, menu_col = st.columns(2, gap="small")
                pdf_key = f"pdf_bytes_{audit_id}"
                pdf_slot = pdf_col.empty()

                if pdf_key in st.session_state:
                    pdf_slot.download_button(
                        "Save PDF",
                        data=st.session_state[pdf_key],
                        file_name=f"seo_audit_{audit_id}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key=f"download_{audit_id}",
                        on_click=_reset_pdf_download,
                        args=(audit_id,),
                    )
                elif pdf_slot.button("PDF", use_container_width=True, key=f"pdf_{audit_id}"):
                    try:
                        response = (
                            supabase.table("audits")
                            .select("json, scraped_data, url")
                            .eq("id", audit_id)
                            .limit(1)
                            .execute()
                        )
                        if not response.data:
                            st.error("Audit record not found.")
                        else:
                            row = response.data[0]
                            st.session_state[pdf_key] = _cached_audit_pdf(
                                audit_id=str(audit_id),
                                report_json=row["json"],
                                scraped_json=json.dumps(
                                    _safe_json(row.get("scraped_data", {}))
                                ),
                                page_url=row.get("url", url),
                                site_title=title,
                            )
                            st.session_state.pop(f"pdf_error_{audit_id}", None)
                            st.rerun()
                    except Exception:
                        logger.exception("Could not generate PDF for audit %s", audit_id)
                        st.session_state[f"pdf_error_{audit_id}"] = (
                            "PDF generation is temporarily unavailable."
                        )
                        st.rerun()

                if f"pdf_error_{audit_id}" in st.session_state:
                    st.error(st.session_state[f"pdf_error_{audit_id}"])

                with menu_col.popover("Actions", use_container_width=True):
                    if not archived:
                        if st.button("Archive", use_container_width=True, key=f"archive_{audit_id}"):
                            supabase.table("audits").update({"is_archived": True}).eq("id", audit_id).execute()
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        if st.button("Restore", use_container_width=True, key=f"restore_{audit_id}"):
                            supabase.table("audits").update({"is_archived": False}).eq("id", audit_id).execute()
                            st.cache_data.clear()
                            st.rerun()

                    if st.button("Delete", use_container_width=True, key=f"delete_{audit_id}"):
                        supabase.table("audits").delete().eq("id", audit_id).execute()
                        st.cache_data.clear()
                        st.rerun()

    active_tab, archived_tab = st.tabs(["All audits", "Archived"])
    with active_tab:
        if not active_audits:
            st.info("No active audits found.")
        for audit in active_audits:
            render_audit_card(audit, archived=False)

    with archived_tab:
        if not archived_audits:
            st.info("No archived audits found.")
        for audit in archived_audits:
            render_audit_card(audit, archived=True)


# ─────────────────────────────────────────────────────────────────────────────
# Public view
# ─────────────────────────────────────────────────────────────────────────────


def historyView():
    st.html(PAGE_CSS)

    if "active_audit_id" not in st.session_state:
        st.session_state.active_audit_id = None

    supabase = cached_supabase()

    if st.session_state.active_audit_id:
        with st.spinner("Loading audit dashboard..."):
            response = (
                supabase.table("audits")
                .select("*")
                .eq("id", st.session_state.active_audit_id)
                .limit(1)
                .execute()
            )
        if not response.data:
            st.error("Audit record not found.")
            return
        _render_audit_report(supabase, response.data[0])
    else:
        _render_audit_list(supabase)


