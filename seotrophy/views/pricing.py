import os
import base64
from pathlib import Path
from html import escape

import dotenv
import streamlit as st
import stripe


dotenv.load_dotenv()

# Use your Stripe secret key here, never a publishable key.
stripe.api_key = os.getenv("STRIPE_KEY")

APP_URL = os.getenv("APP_URL", "http://192.168.2.68:8501")


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"
STRIPE_LOGO_PATH = STATIC_DIR / "stripe.png"


# ------------------------------------------------------------
# Pricing data
# ------------------------------------------------------------

PACK_DEFINITIONS = [
    {
        "title": "10 Credits",
        "price": "$4",
        "amount_cents": 400,
        "credits": 10,
        "description": "Best for trying seotrophy or running a small one-time SEO audit batch.",
        "benefits": [
            "10 audit credits included",
            "No subscription required",
            "Credits do not expire",
            "Priority email support",
        ],
        "featured": False,
        "badge": "Starter",
    },
    {
        "title": "25 Credits",
        "price": "$9",
        "amount_cents": 900,
        "credits": 25,
        "description": "The most balanced pack for regular audits, landing pages, and small campaigns.",
        "benefits": [
            "25 audit credits included",
            "Best value for regular usage",
            "Credits do not expire",
            "Priority email support",
        ],
        "featured": True,
        "badge": "Most popular",
    },
    {
        "title": "60 Credits",
        "price": "$19",
        "amount_cents": 1900,
        "credits": 60,
        "description": "Designed for heavier audit workflows, agencies, and multi-domain analysis.",
        "benefits": [
            "60 audit credits included",
            "Lowest cost per audit",
            "Credits do not expire",
            "Priority email support",
        ],
        "featured": False,
        "badge": "Scale",
    },
]


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _load_base64_image(path: Path) -> str | None:
    try:
        if not path.exists():
            return None

        with open(path, "rb") as file:
            return base64.b64encode(file.read()).decode()

    except Exception:
        return None


def _format_cents_per_credit(amount_cents: int, credits: int) -> str:
    if not amount_cents or not credits:
        return "$0.00"

    value = amount_cents / credits / 100
    return f"${value:.2f}"


def create_checkout_session(pack: dict, user_id: str):
    """
    Creates a Stripe Checkout Session for a one-time credit pack purchase.
    """

    if not stripe.api_key:
        raise RuntimeError("Stripe secret key is missing. Please set STRIPE_KEY in your environment.")

    user_email = st.session_state.get("email")

    if not user_email:
        raise RuntimeError("User email is missing from session state.")

    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=user_email,
        payment_intent_data={
            "receipt_email": user_email,
        },
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": pack["title"],
                        "description": pack["description"],
                    },
                    "unit_amount": pack["amount_cents"],
                },
                "quantity": 1,
            }
        ],
        success_url=f"{APP_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{APP_URL}?payment=cancelled",
        client_reference_id=user_id,
        metadata={
            "user_id": user_id,
            "credits": str(pack["credits"]),
            "plan_title": pack["title"],
        },
    )

    return session


def _inject_pricing_styles() -> None:
    st.html(
        """
        <style>
        :root {
            --st-bg: #ffffff;
            --st-surface: #ffffff;
            --st-surface-muted: #f7f7f7;
            --st-surface-hover: #f2f2f2;

            --st-text: #0f0f0f;
            --st-muted: #5f6368;
            --st-soft-muted: #8a8f98;
            --st-inverse-text: #ffffff;

            --st-border: #e5e5e5;
            --st-border-strong: #cfcfcf;

            --st-primary: #0f0f0f;
            --st-primary-hover: #272727;
            --st-primary-soft: rgba(15, 15, 15, 0.06);

            --st-radius-lg: 18px;
            --st-radius-md: 12px;
            --st-radius-sm: 8px;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(201, 150, 47, 0.10), transparent 26rem),
                radial-gradient(circle at 88% 18%, rgba(20, 19, 15, 0.055), transparent 24rem),

                repeating-linear-gradient(0deg,
                    transparent, transparent 49px,
                    rgba(20, 19, 15, 0.08) 49px,
                    rgba(20, 19, 15, 0.08) 50px
                ),
                repeating-linear-gradient(90deg,
                    transparent, transparent 49px,
                    rgba(20, 19, 15, 0.08) 49px,
                    rgba(20, 19, 15, 0.08) 50px
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
            position: relative;
            padding-top: 2.5rem;
            padding-bottom: 4rem;
            max-width: 80% !important;
            isolation: isolate;
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

        ::selection {
            background: var(--st-text);
            color: var(--st-inverse-text);
        }

        /* ----------------------------------------------------
           Header
        ---------------------------------------------------- */

        .pricing-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 2rem;
            margin-bottom: 1.4rem;
        }

        .pricing-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.38rem 0.7rem;
            border: 1px solid var(--st-border);
            border-radius: 999px;
            background: var(--st-surface);
            color: var(--st-muted);
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            margin-bottom: 0.85rem;
        }

        .pricing-kicker-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: var(--st-primary);
            display: inline-block;
        }

        .pricing-title {
            margin: 0;
            color: var(--st-text);
            font-size: clamp(2rem, 4vw, 3.3rem);
            line-height: 1.02;
            letter-spacing: -0.065em;
            font-weight: 850;
        }

        .pricing-subtitle {
            margin: 1rem 0 0 0;
            max-width: 720px;
            color: var(--st-muted);
            font-size: 1rem;
            line-height: 1.65;
        }

        .balance-card {
            min-width: 235px;
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            border-radius: var(--st-radius-md);
            padding: 1rem;
        }

        .balance-label {
            color: var(--st-soft-muted);
            font-size: 0.72rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.45rem;
        }

        .balance-value {
            color: var(--st-text);
            font-size: 1.8rem;
            line-height: 1;
            font-weight: 850;
            letter-spacing: -0.05em;
        }

        .balance-caption {
            margin-top: 0.55rem;
            color: var(--st-muted);
            font-size: 0.82rem;
            line-height: 1.45;
        }

        /* ----------------------------------------------------
           Trust row
        ---------------------------------------------------- */

        .trust-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin: 1.4rem 0 2rem 0;
        }

        .trust-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.55rem 0.8rem;
            border-radius: 999px;
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            color: var(--st-muted);
            font-size: 0.86rem;
            font-weight: 650;
        }

        .trust-pill::before {
            content: "";
            width: 6px;
            height: 6px;
            border-radius: 999px;
            background: var(--st-text);
            display: inline-block;
            opacity: 0.88;
        }

        /* ----------------------------------------------------
           Pricing cards
        ---------------------------------------------------- */

        .plan-card {
            height: 100%;
            border: 1px solid var(--st-border);
            background: var(--st-surface);
            border-radius: var(--st-radius-lg);
            padding: 1.25rem;
            margin-bottom: 0.75rem;
        }

        .plan-card.featured {
            border: 1.5px solid var(--st-text);
        }

        .plan-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            padding: 0.34rem 0.65rem;
            margin-bottom: 1rem;
            font-size: 0.72rem;
            font-weight: 780;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            border: 1px solid var(--st-border);
            color: var(--st-muted);
            background: var(--st-surface-muted);
        }

        .plan-badge.featured {
            background: var(--st-text);
            color: var(--st-inverse-text);
            border-color: var(--st-text);
        }

        .plan-title {
            margin: 0;
            color: var(--st-text);
            font-size: 1.15rem;
            line-height: 1.25;
            font-weight: 800;
            letter-spacing: -0.025em;
        }

        .plan-description {
            min-height: 4.3rem;
            margin: 0.55rem 0 1.1rem 0;
            color: var(--st-muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .plan-price-row {
            display: flex;
            align-items: flex-end;
            gap: 0.45rem;
            margin-bottom: 0.3rem;
        }

        .plan-price {
            color: var(--st-text);
            font-size: 2.35rem;
            line-height: 1;
            font-weight: 1000;
            letter-spacing: -0.06em;
        }

        .plan-price-caption {
            color: var(--st-muted);
            font-size: 0.86rem;
            line-height: 1.25;
            padding-bottom: 0.16rem;
        }

        .plan-unit {
            color: var(--st-soft-muted);
            font-size: 0.82rem;
            margin-bottom: 1.1rem;
        }

        .plan-divider {
            border: none;
            border-top: 1px solid var(--st-border);
            margin: 1rem 0;
        }

        .plan-list {
            margin: 0;
            padding: 0;
            list-style: none;
        }

        .plan-list li {
            display: flex;
            align-items: flex-start;
            gap: 0.55rem;
            margin-bottom: 0.68rem;
            color: var(--st-text);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .plan-list li::before {
            content: "✓";
            color: var(--st-text);
            font-weight: 900;
            flex-shrink: 0;
            margin-top: 0.02rem;
        }

        /* ----------------------------------------------------
           Native Streamlit button polish
        ---------------------------------------------------- */

        .stButton > button {
            min-height: 2.75rem !important;
            border-radius: 999px !important;
            font-weight: 760 !important;
            letter-spacing: -0.01em !important;
        }

        .stButton > button[kind="primary"] {
            background: var(--st-primary) !important;
            color: var(--st-inverse-text) !important;
            border: 1px solid var(--st-primary) !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: var(--st-primary-hover) !important;
            border-color: var(--st-primary-hover) !important;
        }

        .stButton > button[kind="secondary"] {
            background: var(--st-surface) !important;
            color: var(--st-text) !important;
            border: 1px solid var(--st-border-strong) !important;
        }

        .stButton > button[kind="secondary"]:hover {
            background: var(--st-surface-hover) !important;
            border-color: var(--st-text) !important;
        }

        .stLinkButton > a {
            border-radius: 999px !important;
            font-weight: 760 !important;
        }

        /* ----------------------------------------------------
           Checkout panel and footer
        ---------------------------------------------------- */

        .checkout-panel {
            margin-top: 0rem;
            border: 1px solid var(--st-border);
            background: var(--st-surface-muted);
            border-radius: var(--st-radius-lg);
            padding: 1.15rem;
        }

        .checkout-panel-title {
            margin: 0;
            color: var(--st-text);
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .checkout-panel-text {
            margin: 0.4rem 0 0 0;
            color: var(--st-muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .pricing-footer {
            margin-top: 2rem;
            border-top: 1px solid var(--st-border);
            padding-top: 1.2rem;
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 0.45rem;
            text-align: center;
            color: var(--st-muted);
            font-size: 0.86rem;
            line-height: 1.5;
        }

        .pricing-footer img {
            height: 18px;
            vertical-align: middle;
            filter: grayscale(1);
        }

        .fine-print {
            margin-top: 0.75rem;
            text-align: center;
            color: var(--st-soft-muted);
            font-size: 0.78rem;
            line-height: 1.5;
        }

        @media (max-width: 900px) {
            .block-container {
                max-width: 94% !important;
                padding-top: 1.4rem !important;
            }

            .pricing-header {
                flex-direction: column;
                align-items: flex-start;
            }

            .balance-card {
                width: 100%;
                min-width: unset;
            }

            .plan-description {
                min-height: unset;
            }
        }
        
        </style>
        
        """
    )

st.html(
    """
    <style>
    div[data-testid="stDialog"] div[role="dialog"],
    div[role="dialog"][aria-modal="true"] {
        border-radius: 10px !important;
        overflow: hidden !important;
        border: 1px solid #e5e5e5 !important;
    }

    div[data-testid="stDialog"] div[role="dialog"] > div,
    div[role="dialog"][aria-modal="true"] > div {
        border-radius: 10px !important;
    }

    div[data-testid="stDialog"] button,
    div[role="dialog"][aria-modal="true"] button {
        border-radius: 999px !important;
    }
    </style>
    """
)

@st.dialog("Continue to Checkout")
def continuation_dialog():
    checkout_url = st.session_state.get("checkout_url")
    selected_plan = st.session_state.get("selected_plan")
    selected_price = st.session_state.get("selected_price")
    if checkout_url:
        st.html(
            f"""
            <div class="checkout-panel">
                <h3 class="checkout-panel-title">Checkout ready</h3>
                <p class="checkout-panel-text">
                    You selected <strong>{escape(str(selected_plan))}</strong> for
                    <strong>{escape(str(selected_price))}</strong>. Continue to Stripe to complete the payment securely.
                </p>
            </div>
            """
        )
        st.info(f"E-mail: {st.session_state.email}", icon=":material/email:")
        st.space("medium")
        st.link_button(
            "Continue to Stripe Checkout",
            checkout_url,
            use_container_width=True,
            type="primary",
            icon=":material/arrow_right_alt:",
            icon_position="right",
        )

def _render_plan_card(pack: dict) -> None:
    badge_class = "plan-badge featured" if pack["featured"] else "plan-badge"
    card_class = "plan-card featured" if pack["featured"] else "plan-card"
    cents_per_credit = _format_cents_per_credit(pack["amount_cents"], pack["credits"])

    benefits_html = "".join(
        f"<li>{escape(benefit)}</li>"
        for benefit in pack["benefits"]
    )

    st.html(
        f"""
        <div class="{card_class}">
            <div class="{badge_class}">{escape(pack["badge"])}</div>

            <h3 class="plan-title">{escape(pack["title"])}</h3>

            <p class="plan-description">
                {escape(pack["description"])}
            </p>

            <div class="plan-price-row">
                <div class="plan-price">{escape(pack["price"])}</div>
                <div class="plan-price-caption">one-time</div>
            </div>

            <div class="plan-unit">
                {cents_per_credit} per credit
            </div>

            <hr class="plan-divider">

            <ul class="plan-list">
                {benefits_html}
            </ul>
        </div>
        """
    )


# ------------------------------------------------------------
# Main view
# ------------------------------------------------------------

def pricingView():
    _inject_pricing_styles()

    user_id = st.session_state.get("uid")
    user_email = st.session_state.get("email")
    credits_left = st.session_state.get("credits", 0)

    if not user_id:
        st.error("You need to be logged in to purchase credits.")
        return

    stripe_logo = _load_base64_image(STRIPE_LOGO_PATH)

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    st.space("small")

    st.html(
        f"""
        <div class="pricing-header">
            <div>
                <h1 class="pricing-title">Simple credit packs for serious SEO audits.</h1><br>

                <p class="pricing-subtitle">
                    Buy credits only when you need them. No monthly subscription, no hidden usage lock-in,
                    and no complicated pricing model.
                </p>
            </div>

            <div class="balance-card">
                <div class="balance-label">Current balance</div>
                <div class="balance-value">{int(credits_left):,}</div>
                <div class="balance-caption">
                    Available audit credits on your account.
                </div>
            </div>
        </div>
        """
    )

    st.html(
        """
        <div class="trust-row">
            <div class="trust-pill">One-time payments</div>
            <div class="trust-pill">Credits do not expire</div>
            <div class="trust-pill">Secure Stripe checkout</div>
            <div class="trust-pill">Receipt sent by email</div>
            <div class="trust-pill">Priority support included</div>
        </div>
        """
    )

    # --------------------------------------------------------
    # Pricing cards
    # --------------------------------------------------------

    cols = st.columns(3, gap="large")

    for idx, (column, pack) in enumerate(zip(cols, PACK_DEFINITIONS)):
        with column:
            _render_plan_card(pack)

            button_type = "primary" if pack["featured"] else "secondary"

            if st.button(
                f"Select {pack['title']}",
                key=f"select_{idx}_{pack['title'].replace(' ', '_')}",
                use_container_width=True,
                type=button_type,
            ):
                with st.spinner("Creating secure checkout session..."):
                    try:
                        session = create_checkout_session(pack, user_id)

                        st.session_state.selected_plan = pack["title"]
                        st.session_state.selected_price = pack["price"]
                        st.session_state.selected_plan_index = idx
                        st.session_state.checkout_url = session.url

                        continuation_dialog()

                    except Exception as error:
                        st.error(f"Could not start checkout: {error}")

    # --------------------------------------------------------
    # Checkout continuation panel
    # --------------------------------------------------------

    

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    if stripe_logo:
        stripe_markup = f'<img src="data:image/png;base64,{stripe_logo}" alt="Stripe logo">'
    else:
        stripe_markup = "<strong>Stripe</strong>"

    st.html(
        f"""
        <div class="pricing-footer">
            <span>Payments are processed securely through</span>
            {stripe_markup}
            <span>for account <b><u>{escape(str(user_email or ""))}</u></b>.</span>
        </div>

        <div class="fine-print">
            Credits are added after payment confirmation through the Stripe webhook.
            If credits do not appear immediately, refresh the app after a few seconds.
        </div>
        """
    )

    params = st.query_params

    if params.get("payment") == "success":
        st.success("Payment completed. Credits will be added after Stripe confirms the webhook event.")

    elif params.get("payment") == "cancelled":
        st.info("Checkout was cancelled. No payment was completed.")