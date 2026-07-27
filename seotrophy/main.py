import textwrap
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from views import home, login, audit, history, settings, pricing, api, landing
from utils import cached_supabase, _qp, _clear_query_params, _build_receipt_pdf
from html import escape


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

LOGO_FULL = str(STATIC_DIR / "full_logo.png")
LOGO_SMALL = str(STATIC_DIR / "full_logo_small.png")


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------

st.set_page_config(
    page_title="Seotrophy",
    page_icon="seotrophy/static/de.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ------------------------------------------------------------
# Route helper
# ------------------------------------------------------------

def _current_route_slug() -> str:
    try:
        path = urlparse(st.context.url).path.rstrip("/")
    except Exception:
        return ""

    if not path:
        return ""

    return path.rsplit("/", 1)[-1]


# ------------------------------------------------------------
# CSS helpers
# ------------------------------------------------------------

def _inject_global_styles() -> None:
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Google+Sans:ital,opsz,wght@0,17..18,400..700;1,17..18,400..700&display=swap');
            * {
                font-family: 'Google Sans';
            }

            ::selection {
                background: #cb785c;
                color: #ffffff;
            }

          

            .receipt-card {
                max-width: 760px;
                margin: 2rem auto 1.5rem auto;
                padding: 2rem 1.6rem;
                border: 1px solid #e2e8f0;
                border-radius: 24px;
                background: #ffffff;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
                text-align: center;
            }

            .receipt-title {
                margin-bottom: 0.5rem;
                color: #0f172a;
                font-size: 2rem;
                font-weight: 750;
                letter-spacing: -0.03em;
            }

            .receipt-subtitle {
                margin: 0;
                color: #475569;
                line-height: 1.6;
                font-size: 1rem;
            }

            .receipt-meta {
                margin-top: 1rem;
                color: #64748b;
                font-size: 0.92rem;
            }

            .receipt-divider {
                margin: 1.25rem 0;
                border: none;
                border-top: 1px solid #e2e8f0;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_landing_styles() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            .block-container {
                padding-top: 0px !important;
                padding-bottom: 4rem !important;
            }

            .stApp {
                overflow-x: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_login_styles() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            header[data-testid="stHeader"] {
                display: none !important;
            }

            .block-container {
                padding-top: 2.25rem !important;
                padding-bottom: 4rem !important;
                max-width: 40% !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _inject_app_shell_styles() -> None:
    st.markdown(
        """
        <style>
            header[data-testid="stHeader"] {
                display: block !important;
                visibility: visible !important;
            }

            [data-testid="stSidebar"] {
                display: block !important;
                visibility: visible !important;
            }

            [data-testid="collapsedControl"] {
                display: flex !important;
                visibility: visible !important;
            }

            .block-container {
                padding-top: 2.25rem !important;
                padding-bottom: 4rem !important;
                max-width: 90% !important;
                
            }
            
        </style>
        """,
        unsafe_allow_html=True,
    )

def _inject_receipt_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --receipt-bg: #ffffff;
            --receipt-surface: #ffffff;
            --receipt-muted-surface: #f7f7f7;
            --receipt-text: #0f0f0f;
            --receipt-muted: #5f6368;
            --receipt-soft-muted: #8a8f98;
            --receipt-border: #e5e5e5;
            --receipt-border-strong: #cfcfcf;
            --receipt-radius-lg: 22px;
            --receipt-radius-md: 14px;
        }

        .block-container {
            max-width: 900px !important;
            padding-top: 3rem !important;
            padding-bottom: 4rem !important;
        }

        .receipt-shell {
            width: 100%;
            margin: 0 auto;
        }

        .receipt-card {
            border: 1px solid var(--receipt-border);
            background: var(--receipt-surface);
            border-radius: var(--receipt-radius-lg);
            padding: 2rem;
            margin-bottom: 1rem;
        }

        .receipt-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1.5rem;
            margin-bottom: 1.6rem;
        }

        .receipt-status-group {
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }

        .receipt-icon {
            width: 42px;
            height: 42px;
            border-radius: 999px;
            border: 1px solid var(--receipt-text);
            background: var(--receipt-text);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.15rem;
            font-weight: 850;
            flex-shrink: 0;
        }

        .receipt-icon.cancelled {
            background: #ffffff;
            color: var(--receipt-text);
            border-color: var(--receipt-border-strong);
        }

        .receipt-title {
            margin: 0;
            color: var(--receipt-text);
            font-size: clamp(1.8rem, 4vw, 2.65rem);
            line-height: 1.05;
            letter-spacing: -0.06em;
            font-weight: 850;
        }

        .receipt-subtitle {
            margin: 0.75rem 0 0 0;
            color: var(--receipt-muted);
            font-size: 1rem;
            line-height: 1.65;
            max-width: 640px;
        }

        .receipt-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 0.42rem 0.75rem;
            font-size: 0.76rem;
            font-weight: 780;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .badge-success {
            background: var(--receipt-text);
            color: #ffffff;
            border: 1px solid var(--receipt-text);
        }

        .badge-cancel {
            background: var(--receipt-muted-surface);
            color: var(--receipt-text);
            border: 1px solid var(--receipt-border);
        }

        .receipt-summary {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin-bottom: 1rem;
        }

        .summary-item {
            border: 1px solid var(--receipt-border);
            background: var(--receipt-muted-surface);
            border-radius: var(--receipt-radius-md);
            padding: 1rem;
        }

        .summary-label {
            color: var(--receipt-soft-muted);
            font-size: 0.72rem;
            font-weight: 760;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
        }

        .summary-value {
            color: var(--receipt-text);
            font-size: 1.15rem;
            font-weight: 820;
            letter-spacing: -0.03em;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }

        .receipt-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }

        .receipt-panel {
            border: 1px solid var(--receipt-border);
            background: var(--receipt-surface);
            border-radius: var(--receipt-radius-md);
            padding: 1.15rem;
        }

        .panel-title {
            margin: 0 0 1rem 0;
            color: var(--receipt-text);
            font-size: 0.96rem;
            font-weight: 820;
            letter-spacing: -0.02em;
        }

        .detail-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            padding: 0.7rem 0;
            border-top: 1px solid var(--receipt-border);
        }

        .detail-row:first-of-type {
            border-top: none;
            padding-top: 0;
        }

        .detail-label {
            color: var(--receipt-muted);
            font-size: 0.86rem;
            line-height: 1.4;
        }

        .detail-value {
            color: var(--receipt-text);
            font-size: 0.86rem;
            line-height: 1.4;
            font-weight: 720;
            text-align: right;
            overflow-wrap: anywhere;
            max-width: 60%;
        }

        .receipt-note {
            margin-top: 1rem;
            border: 1px solid var(--receipt-border);
            background: var(--receipt-muted-surface);
            border-radius: var(--receipt-radius-md);
            padding: 1rem;
            color: var(--receipt-muted);
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .receipt-actions {
            margin-top: 1rem;
        }

        .stButton > button,
        .stDownloadButton > button {
            min-height: 2.75rem !important;
            border-radius: 999px !important;
            font-weight: 760 !important;
        }

        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: var(--receipt-text) !important;
            color: #ffffff !important;
            border: 1px solid var(--receipt-text) !important;
        }

        .stButton > button[kind="secondary"],
        .stDownloadButton > button[kind="secondary"] {
            background: #ffffff !important;
            color: var(--receipt-text) !important;
            border: 1px solid var(--receipt-border-strong) !important;
        }

        @media (max-width: 800px) {
            .receipt-card {
                padding: 1.35rem;
            }

            .receipt-header {
                flex-direction: column;
            }

            .receipt-summary,
            .receipt-grid {
                grid-template-columns: 1fr;
            }

            .detail-row {
                flex-direction: column;
                gap: 0.25rem;
            }

            .detail-value {
                text-align: left;
                max-width: 100%;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _receipt_money(amount_total, currency="USD") -> str:
    if amount_total is None:
        return "Pending"

    try:
        return f"${amount_total / 100:.2f} {currency}"
    except Exception:
        return "Pending"


def _receipt_value(value, fallback="Pending") -> str:
    if value is None or value == "":
        return fallback

    return escape(str(value))


def _render_payment_return_screen(supabase=None) -> bool:
    payment_status = _qp("payment")

    if payment_status not in {"success", "cancelled"}:
        return False

    _inject_receipt_styles()

    # --------------------------------------------------------
    # Cancelled checkout
    # --------------------------------------------------------

    if payment_status == "cancelled":
        html = textwrap.dedent(
            """
            <div class="receipt-shell">
                <div class="receipt-card">
                    <div class="receipt-header">
                        <div class="receipt-status-group">
                            <div class="receipt-icon cancelled">×</div>
                            <div>
                                <h1 class="receipt-title">Checkout cancelled</h1>
                                <p class="receipt-subtitle">
                                    No payment was completed, so no credits were added to your account.
                                    You can return to seotrophy and choose a credit pack again whenever you are ready.
                                </p>
                            </div>
                        </div>

                        <div class="receipt-badge badge-cancel">Cancelled</div>
                    </div>

                    <div class="receipt-note">
                        This cancellation does not create a payment record and your account balance remains unchanged.
                    </div>
                </div>
            </div>
            """
        ).strip()

        st.markdown(html, unsafe_allow_html=True)

        left, right = st.columns([1, 1], gap="medium")

        with left:
            if st.button("Return to app", use_container_width=True, type="primary"):
                _clear_query_params()
                st.rerun()

        with right:
            if st.button("Dismiss", use_container_width=True):
                _clear_query_params()
                st.rerun()

        st.stop()
        return True

    # --------------------------------------------------------
    # Successful checkout
    # --------------------------------------------------------

    session_id = _qp("session_id")
    purchase_data = None

    if supabase is not None and session_id:
        try:
            response = (
                supabase.table("stripe_events")
                .select("*")
                .eq("checkout_session_id", session_id)
                .single()
                .execute()
            )
            purchase_data = response.data
        except Exception:
            purchase_data = None

    plan_title = purchase_data.get("plan_title") if purchase_data else None
    credits_added = purchase_data.get("credits_added") if purchase_data else None
    amount_total = purchase_data.get("amount_total") if purchase_data else None
    currency = purchase_data.get("currency", "usd").upper() if purchase_data else "USD"
    event_id = purchase_data.get("event_id") if purchase_data else None
    created_at = purchase_data.get("created_at") if purchase_data else None

    amount_display = _receipt_money(amount_total, currency)
    package_display = _receipt_value(plan_title)
    credits_display = f"+{escape(str(credits_added))}" if credits_added is not None else "Pending"
    session_display = _receipt_value(session_id)
    event_display = _receipt_value(event_id)
    created_display = _receipt_value(created_at)

    html = textwrap.dedent(
        f"""
        <div class="receipt-shell">
            <div class="receipt-card">
                <div class="receipt-header">
                    <div class="receipt-status-group">
                        <div class="receipt-icon">✓</div>
                        <div>
                            <h1 class="receipt-title">Payment successful</h1>
                            <p class="receipt-subtitle">
                                Your purchase was completed securely. A confirmation record has been created,
                                and your credits are being reflected in your seotrophy account.
                            </p>
                        </div>
                    </div>

                    <div class="receipt-badge badge-success">Paid</div>
                </div>

                <div class="receipt-summary">
                    <div class="summary-item">
                        <div class="summary-label">Package</div>
                        <div class="summary-value">{package_display}</div>
                    </div>

                    <div class="summary-item">
                        <div class="summary-label">Credits added</div>
                        <div class="summary-value">{credits_display}</div>
                    </div>

                    <div class="summary-item">
                        <div class="summary-label">Amount paid</div>
                        <div class="summary-value">{escape(amount_display)}</div>
                    </div>
                </div>

                <div class="receipt-grid">
                    <div class="receipt-panel">
                        <h3 class="panel-title">Receipt details</h3>

                        <div class="detail-row">
                            <div class="detail-label">Status</div>
                            <div class="detail-value">Paid</div>
                        </div>

                        <div class="detail-row">
                            <div class="detail-label">Checkout session</div>
                            <div class="detail-value">{session_display}</div>
                        </div>

                        <div class="detail-row">
                            <div class="detail-label">Transaction ID</div>
                            <div class="detail-value">{event_display}</div>
                        </div>
                    </div>

                    <div class="receipt-panel">
                        <h3 class="panel-title">Payment summary</h3>

                        <div class="detail-row">
                            <div class="detail-label">Payment method</div>
                            <div class="detail-value">Stripe Checkout</div>
                        </div>

                        <div class="detail-row">
                            <div class="detail-label">Fulfillment</div>
                            <div class="detail-value">Completed by webhook</div>
                        </div>

                        <div class="detail-row">
                            <div class="detail-label">Processed at</div>
                            <div class="detail-value">{created_display}</div>
                        </div>
                    </div>
                </div>

                <div class="receipt-note">
                    Your receipt is available as a PDF below. If the credit balance does not update immediately,
                    return to the app and refresh after a few seconds while the Stripe webhook finishes syncing.
                </div>
            </div>
        </div>
        """
    ).strip()

    st.html(html)

    if purchase_data is None and session_id:
        st.info("Receipt data is still loading from the database. Refresh in a moment if needed.")

    st.html('<div class="receipt-actions">')

    col1, col2 = st.columns([1, 1], gap="medium")

    with col1:
        if purchase_data:
            pdf_bytes = _build_receipt_pdf(purchase_data, session_id, event_id)

            st.download_button(
                label="Download Receipt PDF",
                data=pdf_bytes,
                file_name=f"receipt_{event_id or session_id[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button(
                "Download Receipt PDF",
                disabled=True,
                use_container_width=True,
                help="Waiting for receipt data...",
            )

    with col2:
        if st.button("Return to Home (Login Required)", use_container_width=True, type="primary", icon=":material/home:"):
            _clear_query_params()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()
    return True

# ------------------------------------------------------------
# Session defaults
# ------------------------------------------------------------

def _ensure_session_defaults() -> None:
    if "uid" not in st.session_state:
        st.session_state.uid = None

    if "email" not in st.session_state:
        st.session_state.email = None

    if "credits" not in st.session_state:
        st.session_state.credits = 0

# ------------------------------------------------------------
# Main app
# ------------------------------------------------------------

def main() -> None:
    _ensure_session_defaults()
    _inject_global_styles()

    supabase = cached_supabase()


    logged_in = st.session_state.get("uid") is not None

    _render_payment_return_screen(supabase=supabase)

    logged_in = st.session_state.get("uid") is not None
    current_route = _current_route_slug()

    protected_routes = {
        "home",
        "new",
        "audits",
        "api",
        "pricing",
        "settings",
    }

    # --------------------------------------------------------
    # Public pages
    # --------------------------------------------------------

    landing_page = st.Page(
        landing.landingView,
        title="Landing",
        url_path="",
        default=True,
        visibility="hidden",
    )

    login_page = st.Page(
        login.loginView,
        title="Login",
        url_path="login",
        visibility="hidden",
    )

    # This page is only used when a logged-out user opens a protected URL.
    # It makes login the default page for that specific run.
    login_gate_page = st.Page(
        login.loginView,
        title="Login",
        url_path="login",
        default=True,
        visibility="hidden",
    )

    # --------------------------------------------------------
    # Protected app pages
    # --------------------------------------------------------

    home_page = st.Page(
        home.homeView,
        title="Home",
        icon=":material/home:",
        url_path="home",
        default=True,
    )

    audit_page = st.Page(
        audit.auditView,
        title="New Audit",
        icon=":material/add:",
        url_path="new",
    )

    history_page = st.Page(
        history.historyView,
        title="My Audits",
        icon=":material/history:",
        url_path="audits",
    )

    api_page = st.Page(
        api.apiView,
        title="API",
        icon=":material/power:",
        url_path="api",
    )

    pricing_page = st.Page(
        pricing.pricingView,
        title="Pricing",
        icon=":material/description:",
        url_path="pricing",
    )

    settings_page = st.Page(
        settings.settingsView,
        title="Settings",
        icon=":material/settings:",
        url_path="settings",
    )

    protected_pages = [
        home_page,
        audit_page,
        history_page,
        api_page,
        pricing_page,
        settings_page,
    ]

    # --------------------------------------------------------
    # Logged-out routing
    # --------------------------------------------------------

    if not logged_in:
        if current_route in protected_routes:
            _inject_login_styles()

            page = st.navigation(
                [login_gate_page],
                position="hidden",
            )

            page.run()
            return

        if current_route == "login":
            _inject_login_styles()
        else:
            _inject_landing_styles()

        page = st.navigation(
            [landing_page, login_page],
            position="hidden",
        )

        page.run()
        return

    # --------------------------------------------------------
    # Logged-in routing
    # --------------------------------------------------------

    _inject_app_shell_styles()

    page = st.navigation(
        protected_pages,
        position="top",
    )

    st.logo(
        LOGO_FULL,
        icon_image=LOGO_FULL,
        size="large",
    )

    page.run()


if __name__ == "__main__":
    main()