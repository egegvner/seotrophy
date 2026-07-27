import datetime as dt
from html import escape

import streamlit as st
from utils import (
    get_user_audits,
    render_credit_analytics_chart,
    get_credit_history_timeline,
)


# ------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------

def _format_number(value) -> str:
    try:
        return f"{int(value):,}"
    except Exception:
        return "0"


def _safe_datetime_from_iso(value):
    if not value:
        return None

    try:
        cleaned = str(value).replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(cleaned)

        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)

        return parsed
    except Exception:
        return None


def _calculate_days_active(user_audits) -> int:
    if not user_audits:
        return 1

    created_dates = []

    for audit in user_audits:
        parsed = _safe_datetime_from_iso(audit.get("created_at"))
        if parsed:
            created_dates.append(parsed)

    if not created_dates:
        return 1

    first_audit_date = min(created_dates)
    return max(1, (dt.datetime.utcnow() - first_audit_date).days)


def _inject_home_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            /* Core surfaces */
            --st-bg: #ffffff;
            --st-surface: #ffffff;
            --st-surface-muted: #f7f7f7;
            --st-surface-hover: #f2f2f2;

            /* Text */
            --st-text: #0f0f0f;
            --st-muted: #5f6368;
            --st-soft-muted: #8a8f98;
            --st-inverse-text: #ffffff;

            /* Borders */
            --st-border: #e5e5e5;
            --st-border-strong: #cfcfcf;

            /* Primary action */
            --st-primary: #0f0f0f;
            --st-primary-hover: #272727;
            --st-primary-soft: rgba(15, 15, 15, 0.06);

            /* Status colors, still monochrome-friendly */
            --st-success: #111111;
            --st-warning: #737373;
            --st-danger: #000000;

            /* Shadows */
            --st-shadow-subtle: 0 1px 2px rgba(0, 0, 0, 0.04);
            --st-shadow-card: 0 8px 24px rgba(0, 0, 0, 0.06);

            /* Radius */
            --st-radius-lg: 18px;
            --st-radius-md: 15px;
            --st-radius-sm: 8px;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(201, 150, 47, 0.10), transparent 26rem),
                radial-gradient(circle at 88% 18%, rgba(20, 19, 15, 0.055), transparent 24rem),

                repeating-linear-gradient(0deg,
                    transparent, transparent 49px,
                    rgba(20, 19, 15, 0.048) 49px,
                    rgba(20, 19, 15, 0.048) 50px
                ),
                repeating-linear-gradient(90deg,
                    transparent, transparent 49px,
                    rgba(20, 19, 15, 0.048) 49px,
                    rgba(20, 19, 15, 0.048) 50px
                ),

                linear-gradient(180deg, #FBFAF7 0%, #F7F6F2 52%, #FBFAF7 100%);

            background-size:
                auto,               /* first radial */
                auto,               /* second radial */
                50px 50px,          /* horizontal lines tile */
                50px 50px,          /* vertical lines tile */
                auto;               /* overall gradient */
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        .block-container {
        backdrop-filter: blur(2px);
            -webkit-backdrop-filter: blur(2px);
            padding-top: 2.1rem !important;
            padding-bottom: 4rem !important;
            max-width: 80% !important;
        }

        .block-container::before {
            content: "";
            position: absolute;

            inset: -10rem;

            pointer-events: none;
            z-index: -1;

            backdrop-filter: blur(2px);
            -webkit-backdrop-filter: blur(2px);

            -webkit-mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            -webkit-mask-composite: source-in;

            mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            mask-composite: intersect;
        }

        html, body, [class*="css"] {
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--st-text);
        }

        /* ----------------------------------------------------
           Page header
        ---------------------------------------------------- */

        .home-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 2rem;
            margin-bottom: 1.8rem;
        }

        .home-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.38rem 0.7rem;
            border: 1px solid var(--st-border);
            border-radius: 999px;
            background: var(--st-surface);
            color: var(--st-muted);
            font-size: 0.76rem;
            font-weight: 650;
            letter-spacing: 0.02em;
            margin-bottom: 0.85rem;
        }

        .home-kicker-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: var(--st-primary);
            display: inline-block;
        }

        .home-title {
            margin: 0;
            font-size: clamp(2rem, 4vw, 3.2rem);
            line-height: 1.02;
            letter-spacing: -0.06em;
            font-weight: 800;
            color: var(--st-text);
        }

        .home-subtitle {
            margin: 0.8rem 0 0 0;
            max-width: 680px;
            color: var(--st-muted);
            font-size: 1rem;
            line-height: 1.65;
        }

        .home-status-card {
            min-width: 230px;
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            border-radius: var(--st-radius-md);
            padding: 1rem;
        }

        .status-label {
            color: var(--st-soft-muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
        }

        .status-value {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--st-text);
            font-size: 0.95rem;
            font-weight: 750;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            background: var(--st-primary);
            display: inline-block;
        }

        .status-caption {
            margin-top: 0.55rem;
            color: var(--st-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }

        /* ----------------------------------------------------
           Section headings
        ---------------------------------------------------- */

        .section-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1.5rem;
            margin: 2.15rem 0 0.9rem 0;
        }

        .section-title {
            margin: 0;
            color: var(--st-text);
            font-size: 1.15rem;
            letter-spacing: -0.025em;
            font-weight: 780;
        }

        .section-description {
            margin: 0.35rem 0 0 0;
            color: var(--st-muted);
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .section-meta {
            color: var(--st-soft-muted);
            font-size: 0.8rem;
            font-weight: 650;
            white-space: nowrap;
        }

        /* ----------------------------------------------------
           Metric cards
        ---------------------------------------------------- */

        .metric-card {
            height: 100%;
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            padding: 1.25rem 1.2rem;
            border-radius: var(--st-radius-md);
        }

        .metric-card:hover {
            border-color: var(--st-border-strong);
        }

        .metric-topline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.15rem;
        }

        .metric-label {
            color: var(--st-muted);
            font-size: 1rem;
            letter-spacing: 0.06em;
            font-weight: 720;
        }

        .metric-chip {
            color: var(--st-primary);
            background: var(--st-primary-soft);
            border: 1px solid rgba(203, 120, 92, 0.16);
            border-radius: 999px;
            padding: 0.25rem 0.55rem;
            font-size: 0.72rem;
            font-weight: 720;
        }

        .metric-value {
            color: var(--st-text);
            font-size: 2.25rem;
            font-weight: 820;
            letter-spacing: -0.055em;
            line-height: 1;
        }

        .metric-caption {
            margin-top: 0.7rem;
            color: var(--st-muted);
            font-size: 0.86rem;
            line-height: 1.5;
        }

        /* ----------------------------------------------------
           Panels
        ---------------------------------------------------- */

        .panel-shell {
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            border-radius: var(--st-radius-lg);
            padding: 1.2rem;
            margin-top: 0.8rem;
        }

        .panel-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .panel-title {
            margin: 0;
            color: var(--st-text);
            font-size: 1rem;
            font-weight: 780;
            letter-spacing: -0.02em;
        }

        .panel-caption {
            margin: 0.35rem 0 0 0;
            color: var(--st-muted);
            font-size: 0.88rem;
            line-height: 1.5;
        }

        .empty-state {
            border: 1px dashed var(--st-border-strong);
            background: var(--st-surface-muted);
            border-radius: var(--st-radius-md);
            padding: 1.5rem;
            color: var(--st-muted);
            font-size: 0.93rem;
            line-height: 1.6;
        }

        /* ----------------------------------------------------
           Streamlit native component polish
        ---------------------------------------------------- */

        [data-testid="stMetric"] {
            border: 1px solid var(--st-border);
            background: var(--st-surface-muted);
            padding: 1rem;
            border-radius: var(--st-radius-md);
        }

        [data-testid="stMetricLabel"] {
            color: var(--st-muted);
            font-size: 0.78rem;
            letter-spacing: 0.04em;
        }

        [data-testid="stMetricValue"] {
            color: var(--st-text);
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        hr {
            border-color: var(--st-border);
        }

        @media (max-width: 900px) {
            .home-header {
                flex-direction: column;
            }

            .home-status-card {
                width: 100%;
                min-width: unset;
            }

            .section-header {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.35rem;
            }

            .section-meta {
                white-space: normal;
            }
        }

        
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(label: str, value: str, caption: str, chip: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-topline">
                <div class="metric-label">{escape(label)}</div>
                <div class="metric-chip">{escape(chip)}</div>
            </div>
            <div class="metric-value">{escape(value)}</div>
            <div class="metric-caption">{escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Main view
# ------------------------------------------------------------

def homeView():
    _inject_home_styles()

    credits_left = st.session_state.get("credits", 0)

    with st.spinner("Syncing workspace..."):
        user_audits = get_user_audits(st.session_state.uid)
        total_audits = len(user_audits) if user_audits else 0
        days_active = _calculate_days_active(user_audits)

    # --------------------------------------------------------
    # Account metrics
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="section-header">
            <div>
                <h2 class="section-title">Account overview</h2>
            </div>
            <div class="section-meta">Updated live from your account session</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3, gap="medium")

    with m1:
        _metric_card(
            label="Available credits",
            value=_format_number(credits_left),
            caption="Credits currently available for running new SEO audits.",
            chip="Balance",
        )

    with m2:
        _metric_card(
            label="Domains analyzed",
            value=_format_number(total_audits),
            caption="Total completed audit records connected to your account.",
            chip="Usage",
        )

    with m3:
        _metric_card(
            label="Days active",
            value=_format_number(days_active),
            caption="Estimated account activity window based on your first audit.",
            chip="History",
        )

    # --------------------------------------------------------
    # Credit usage
    # --------------------------------------------------------

    
    st.space("medium")
    st.subheader("Credit Usage")

    with st.spinner("Compiling credit activity..."):
        timeline_df = get_credit_history_timeline(st.session_state.uid)

    if not timeline_df.empty:
        render_credit_analytics_chart(timeline_df)

    else:
        st.markdown(
            """
            <div class="empty-state">
                No credit ledger activity is available for this profile yet.
                Once credits are purchased or consumed, your usage timeline will appear here.
            </div>
            """,
            unsafe_allow_html=True,
        )