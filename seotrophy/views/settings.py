import streamlit as st
import pandas as pd
from utils import cached_supabase, get_user_total_purchased_credits

def settingsView():
    st.markdown(
        """
        <style>
        ::selection { background: #cb785c; color: #ffffff; }

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
        .settings-header {
            font-size: 1.1rem;
            color: #64748b;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([10, 1])
    c1.header("Account Setings", width="stretch")
    if c2.button("Logout", type="primary", icon=":material/exit_to_app:", use_container_width=True):
        st.session_state.uid = None
        st.session_state.email = None
        st.session_state.credits = 0
        st.rerun()
    st.markdown("<p class='settings-header'>Manage your profile, active developer keys, and audit preferences.</p>", unsafe_allow_html=True)

    tab_profile, tab_api, tab_preferences = st.tabs([
        "Profile & Subscription", 
        "Developer Keys", 
        "Audit Engine Defaults"
    ])

    with tab_profile:
        st.subheader("Account Identity")
        
        col_email, col_tier = st.columns(2)
        with col_email:
            st.text_input("Registered Email Address", value=st.session_state.get("email", ""), disabled=True)
            st.caption("Your identity is verified via Supabase Auth.")
        
        with col_tier:
            credits = st.session_state.get("credits", 0)
            user_tier = "Enterprise" if credits > 50 else "Pro Specialist" if credits > 0 else "Free Tier"
            st.text_input("Current Plan Status", value=user_tier, disabled=True)
            st.caption("To upgrade your quota constraints, head over to the Pricing tab.")

        st.divider()
        st.subheader("Usage Summary")
        
        with st.spinner("Calculating allocations..."):
            max_credits = get_user_total_purchased_credits(st.session_state.uid)
        
        current_credits = max(0, credits)
        progress_val = min(1.0, float(current_credits / max_credits))
        
        st.markdown(f"Remaining Crawl Allocation: **{current_credits}** / **{max_credits} Credits**")
        st.progress(progress_val)
        st.caption(f"You have used **{max_credits - current_credits}** of your lifetime aggregated credit capacity.")

    with tab_api:
        st.subheader("Application Programming Interface (API)")
        st.markdown(
            """
            Integrate your autonomous SEO audit engine directly into external CI/CD pipelines, 
            custom dashboards, or automated cron-jobs.
            """
        )

        with st.container(border=True):
            st.markdown("**Active Secret Token**")
            mock_key = f"sk_live_{st.session_state.get('uid', 'default')[:12]}xxxxxxxxxxxx"
            
            col_key, col_copy = st.columns([4, 1], vertical_alignment="center")
            with col_key:
                st.code(mock_key, language="text")
            with col_copy:
                if st.button("Regenerate Key", use_container_width=True):
                    st.toast("Key generation initiated...", icon="🔄")

            st.caption("🚨 Treat this token as a password. Never commit it to public repositories.")

        st.markdown("### Webhook Integration Status")
        st.info("Stripe Payment Webhook Fulfillment Sync: **Operational (Connected via Supabase Edge)**")

    with tab_preferences:
        st.subheader("Reporting Localization")
        
        st.selectbox(
            "Default Executive Summary Language",
            options=["English (US)", "English (UK)"],
            help="Your prompt pipeline currently restricts output to English to match the UI layout framework."
        )

        st.write("<br>", unsafe_allow_html=True)
        if st.button("Save System Preferences", type="primary"):
            st.toast("System defaults successfully compiled!", icon="💾")