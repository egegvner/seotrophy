import streamlit as st
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from utils import cached_supabase, validate_password

def _inject_login_styles():
    st.markdown(
        """
        <style>
        :root {
            --paper: #F7F6F2;
            --surface: #FFFFFF;
            --ink: #14130F;
            --ink-soft: #6B6759;
            --line: #E7E4DC;
            --line-strong: #D6D1C7;
            --gold: #C9962F;
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
            max-width: 40% !important;
            isolation: isolate;
        }

        .block-container::before {
            content: "";
            position: absolute;

            inset: -10rem;

            pointer-events: none;
            z-index: -1;

            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);

            -webkit-mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            -webkit-mask-composite: source-in;

            mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            mask-composite: intersect;
        }

        div[data-testid="stImage"] {
            display: flex;
            justify-content: center;
        }

        div[data-testid="stImage"] img {
            max-height: 52px;
            width: auto;
            object-fit: contain;
        }

        div[data-testid="stTabs"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.96), rgba(255,255,255,0.90));
            border: 1px solid rgba(231, 228, 220, 0.95);
            border-radius: 28px;
            padding: 1.1rem 1.15rem 1.25rem 1.15rem;
            box-shadow: 0 28px 80px -48px rgba(20, 19, 15, 0.55);
            backdrop-filter: blur(18px);
        }

        button[data-baseweb="tab"] {
            width: 100%;
            height: 2.65rem;
            margin: 0 !important;
            border-radius: 999px !important;
            color: var(--ink-soft) !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            background: transparent !important;
        }

    
        div[data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }

        /* Form headings */
        h1, h2, h3 {
            color: var(--ink);
            letter-spacing: -0.04em;
        }

        div[data-testid="stMarkdownContainer"] h1,
        div[data-testid="stMarkdownContainer"] h2,
        div[data-testid="stMarkdownContainer"] h3 {
            text-align: center;
            margin-top: 0.2rem;
            margin-bottom: 1.1rem;
        }

        div[data-testid="stFormSubmitButton"] button {
            min-height: 2.95rem;
            border-radius: 999px !important;
            background: var(--ink) !important;
            color: #ffffff !important;
            border: 1px solid var(--ink) !important;
            font-weight: 800 !important;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background: #000000 !important;
            border-color: #000000 !important;
        }

        /* Alerts inside the card */
        div[data-testid="stAlert"] {
            border-radius: 16px !important;
            border: 1px solid var(--line) !important;
        }

        @media (max-width: 700px) {
            .block-container {
                max-width: 94% !important;
                padding-top: 2rem !important;
            }

            div[data-testid="stTabs"] {
                border-radius: 24px;
                padding: 0.9rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def loginView():
    _inject_login_styles()
    ph = PasswordHasher(
        time_cost=2,
        memory_cost=102400,
        parallelism=8,
    )
    
    supabase = cached_supabase()

    st.space("medium")
    c1, c2, c3 = st.columns([1,3,1], gap="large")
    c2.image("seotrophy/static/full_logo.png", width="content")
    st.space("xxlarge")
    st.markdown('''<style>
                        button[data-baseweb="tab"] {
                        font-size: 24px;
                        margin: 0;
                        width: 100%;
                        }
                        </style>
                ''', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Login", "Register"])
    with t1:
        st.header("Login")
        with st.form("login_form"):
            st.space("xxsmall")
            email = st.text_input("Email", key="login_email").lower().strip()
            password = st.text_input("Password", type="password", key="login_password")
            st.space("large")
            if st.form_submit_button("Login", type="primary", use_container_width=True, shortcut="Enter"):
                with st.spinner("Loading..."):
                    if email and password:
                        if not any(char in email or char in password for char in ["'", '"']):
                            result = supabase.table("users").select("*").eq("email", email).execute()
                            users = result.data
                            if not users:
                                st.error("No account found with that email.")
                            else:
                                stored_hash = users[0]["password"]
                                try:
                                    if ph.verify(stored_hash, password):
                                        st.session_state.uid = users[0]["id"]
                                        st.session_state.email = users[0]["email"]
                                        st.session_state.credits = users[0]["credits"]
                                        st.rerun()
                                except VerifyMismatchError:
                                    st.error("Incorrect password.")
                        else:
                            st.warning("Invalid characters in email or password.")
                    else:
                        st.warning("Please enter required fields.")

            st.space("xxsmall")

    with t2:
        st.header("Register")
        with st.form("register_form"):
            st.space("xxsmall")
            new_email = st.text_input("New Email", key="register_email").lower().strip()
            new_password = st.text_input("New Password", type="password", key="register_password")
            new_password_confirm = st.text_input("Confirm New Password", type="password", key="confirm_password")
            check = st.checkbox("I accept the [terms & conditions](https://www.google.com/) and [privacy statement](https://www.google.com/).")
            st.space("large")
            if st.form_submit_button("Register", type="primary", use_container_width=True, shortcut="Enter"):
                with st.spinner("Loading..."):
                    if new_email and new_password and new_password_confirm:
                        if not any(char in new_email or char in new_password for char in ["'", '"']):
                            if new_password == new_password_confirm:
                                is_valid, message = validate_password(new_password)
                                if not is_valid:
                                    st.warning(message, icon=":material/warning:")
                                elif check:
                                    existing_user = supabase.table("users").select("*").eq("email", new_email).execute()
                                    if existing_user.data:
                                        st.warning("An user with this email already exists.", icon=":material/warning:")
                                    else:
                                        hashed_password = ph.hash(new_password)
                                        supabase.table("users").insert({
                                            "email": new_email,
                                            "password": hashed_password
                                        }).execute()
                                        users = supabase.table("users").select("*").eq("email", new_email).execute().data
                                        st.success("Registration successful!")
                                        st.session_state.uid = users[0]["id"]
                                        st.session_state.email = users[0]["email"]
                                        st.session_state.credits = users[0]["credits"]
                                        st.rerun()
                                else:
                                    st.warning("Please read & accept the terms & conditions and privacy statement.", icon=":material/warning:")
                            else:
                                st.warning("Passwords do not match.", icon=":material/warning:")
                        else:
                            st.warning("Invalid characters in email or password.")
                    else:
                        st.warning("Please enter the required fields.", icon=":material/warning:")
            st.space("xxsmall")
