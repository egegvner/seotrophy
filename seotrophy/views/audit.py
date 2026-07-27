import json
import time
from urllib.parse import urlparse

import streamlit as st

from pipeline import (
    OLLAMA_MODEL,
    SEOAuditReport,
    run_local_seo_audit,
    scrape_seo_targets,
)
from utils import (
    cached_supabase,
    capture_attention_map_data,
    save_attention_map_artifact,
)


PAGE_CSS = """
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

            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);

            -webkit-mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            -webkit-mask-composite: source-in;

            mask-image:
                linear-gradient(to right, transparent 0%, black 14%, black 86%, transparent 100%),
                linear-gradient(to bottom, transparent 0%, black 14%, black 86%, transparent 100%);
            mask-composite: intersect;
        }

.audit-info-card {
    border: 1px solid #d1fae5;
    background: rgba(34, 197, 94, 0.06);
    border-left: 4px solid #22C55E;
    padding: 1rem 1.1rem;
    border-radius: 12px;
    margin-top: 1rem;
    line-height: 1.6;
}
.audit-warning-card {
    border: 1px solid #fed7aa;
    background: rgba(245, 158, 11, 0.07);
    border-left: 4px solid #F59E0B;
    padding: 1rem 1.1rem;
    border-radius: 12px;
    margin-top: 1rem;
    line-height: 1.6;
}
/* Modal dialog styling */
div[data-testid="stDialog"] div[role="dialog"],
div[role="dialog"][aria-modal="true"] {
    border-radius: 22px !important;
    border: 1px solid #e5e5e5 !important;
    overflow: hidden !important;
}

.audit-progress-shell {
    padding: 0.2rem 0 0.4rem 0;
}

.audit-progress-kicker {
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.7rem;
    border-radius: 999px;
    border: 1px solid #e5e5e5;
    background: #f7f7f7;
    color: #5f6368;
    font-size: 0.74rem;
    font-weight: 750;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.85rem;
}

.audit-progress-title {
    margin: 0;
    color: #0f0f0f;
    font-size: 1.55rem;
    line-height: 1.1;
    font-weight: 850;
    letter-spacing: -0.05em;
}

.audit-progress-subtitle {
    margin: 0.65rem 0 1.15rem 0;
    color: #5f6368;
    font-size: 0.92rem;
    line-height: 1.6;
}

.audit-step-list {
    display: grid;
    gap: 0.55rem;
    margin-top: 1rem;
}

.audit-step {
    display: flex;
    align-items: flex-start;
    gap: 0.65rem;
    border: 1px solid #e5e5e5;
    background: #ffffff;
    border-radius: 14px;
    padding: 0.78rem 0.85rem;
}

.audit-step.active {
    border-color: #0f0f0f;
    background: #f7f7f7;
}

.audit-step.done {
    background: #ffffff;
}

.audit-step-marker {
    width: 22px;
    height: 22px;
    border-radius: 999px;
    border: 1px solid #0f0f0f;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0f0f0f;
    font-size: 0.72rem;
    font-weight: 850;
    flex-shrink: 0;
}

.audit-step.done .audit-step-marker,
.audit-step.active .audit-step-marker {
    background: #0f0f0f;
    color: #ffffff;
}

.audit-step-title {
    color: #0f0f0f;
    font-size: 0.9rem;
    font-weight: 780;
    line-height: 1.35;
}

.audit-step-detail {
    color: #5f6368;
    font-size: 0.8rem;
    line-height: 1.45;
    margin-top: 0.15rem;
}

.audit-progress-result {
    margin-top: 1rem;
    border: 1px solid #e5e5e5;
    background: #f7f7f7;
    border-radius: 16px;
    padding: 1rem;
    color: #0f0f0f;
    font-size: 0.9rem;
    line-height: 1.6;
}
</style>
"""


def _json_dumps(data: dict) -> str:
    """Stable JSON string for Streamlit cache keys and model input."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)


def _validate_url(raw: str) -> tuple[bool, str]:
    url = (raw or "").strip()
    if not url:
        return False, ""

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    host = parsed.netloc.strip()

    if parsed.scheme not in {"http", "https"}:
        return False, url
    if not host or "." not in host:
        return False, url
    if " " in url:
        return False, url

    return True, url


def _safe_credits() -> int:
    try:
        return int(st.session_state.get("credits", 0) or 0)
    except Exception:
        return 0


def _looks_like_llm_fallback(report: SEOAuditReport) -> bool:
    """
    Detect whether the narrative layer probably failed.
    The pipeline should still return a useful deterministic report either way.
    """
    joined = " ".join([
        report.title_issue or "",
        report.meta_issue or "",
        report.action_item_markdown or "",
    ]).lower()
    failure_markers = [
        "ollama service is not running",
        "failed to finish inference",
        "ai response",
        "schema validation failed",
        "repair failed",
        "not valid json",
    ]
    return any(marker in joined for marker in failure_markers)


@st.cache_data(ttl=300, show_spinner=False)
def cached_scrape(url: str, options_json: str) -> dict:
    scrape_options = json.loads(options_json)
    return scrape_seo_targets(
        url,
        scrape_timeout=scrape_options.get("scrape_timeout"),
        body_snippet_chars=scrape_options.get("body_snippet_chars"),
    )


@st.cache_data(ttl=300, show_spinner=False)
def cached_audit(scraped_json: str, options_json: str) -> dict:
    scraped_data = json.loads(scraped_json)
    tuning_options = json.loads(options_json)
    report = run_local_seo_audit(scraped_data, tuning_options)
    return report.model_dump(mode="json")


def _completion_message(
    *,
    saved_audit_id: str | None,
    visual_map_enabled: bool,
    visual_map_saved: bool,
    visual_map_error: str | None,
    llm_fallback_used: bool,
) -> tuple[str, str]:
    """
    Returns (tone, message). Tone is success, warning, or info.
    This is the only successful post-audit user-facing message.
    """
    if saved_audit_id is None:
        return (
            "warning",
            "The audit completed, but the saved audit ID could not be confirmed. Please check Audit History before running it again.",
        )

    parts = ["Audit completed and saved to History."]

    if visual_map_enabled and visual_map_saved:
        parts.append("The Page X-Ray Site Map was also generated and attached to the audit.")
    elif visual_map_enabled and visual_map_error:
        parts.append("The audit was saved, but the Page X-Ray Site Map could not be generated.")
    elif not visual_map_enabled:
        parts.append("Page X-Ray Site Map generation was disabled for this run.")

    if llm_fallback_used:
        parts.append("The report used the deterministic fallback because the model response was incomplete or unavailable.")

    tone = "success"
    if visual_map_error or llm_fallback_used:
        tone = "warning"

    return tone, " ".join(parts)

def _render_step_list(active_index: int, completed_indexes: set[int], step_details: dict[int, str]) -> str:
    steps = [
        "Crawl website",
        "Generate Page X-Ray",
        "Build SEO baseline",
        "Run AI analysis",
        "Save report",
        "Final checks",
    ]

    html_steps = []

    for idx, title in enumerate(steps):
        if idx in completed_indexes:
            state = "done"
            marker = "✓"
        elif idx == active_index:
            state = "active"
            marker = str(idx + 1)
        else:
            state = ""
            marker = str(idx + 1)

        detail = step_details.get(idx, "Waiting...")

        html_steps.append(
            f"""
            <div class="audit-step {state}">
                <div class="audit-step-marker">{marker}</div>
                <div>
                    <div class="audit-step-title">{title}</div>
                    <div class="audit-step-detail">{detail}</div>
                </div>
            </div>
            """
        )

    return f'<div class="audit-step-list">{"".join(html_steps)}</div>'


@st.dialog("Running Audit", width="medium")
def _audit_progress_dialog(
    *,
    supabase,
    target_url: str,
    options_json: str,
    credits: int,
    generate_attention_map: bool,
    attention_full_page: bool,
    attention_viewport_width: int,
    attention_viewport_height: int,
):
    st.html(
        f"""
        <div class="audit-progress-shell">
            <div class="audit-progress-kicker">Audit execution</div>
            <h2 class="audit-progress-title">Analyzing your website</h2>
            <p class="audit-progress-subtitle">
                seotrophy is crawling the page, extracting SEO signals, generating the audit report,
                and saving the result to your history. Keep this page open until the process completes.
            </p>
        </div>
        """
    )

    progress_bar = st.progress(0, text="Preparing audit...")
    step_box = st.empty()
    result_box = st.empty()

    completed = set()
    details = {}

    def update_progress(percent: int, active_index: int, detail: str):
        details[active_index] = detail
        progress_bar.progress(percent, text=detail)
        step_box.html(
            _render_step_list(active_index, completed, details)
        )

    attention_map_data = None
    visual_map_error = None
    visual_map_saved = False
    saved_audit_id = None
    llm_fallback_used = False

    update_progress(8, 0, "Crawling live website elements and extracting technical SEO signals...")

    scraped_data = cached_scrape(target_url, options_json)

    if not scraped_data or "error" in scraped_data:
        error_msg = scraped_data.get("error", "Unknown scraping error") if scraped_data else "No data"
        progress_bar.progress(100, text="Audit failed during crawling.")
        result_box.error(f"Could not crawl {target_url}. Reason: {error_msg}")
        st.stop()

    completed.add(0)
    update_progress(24, 1, "Preparing visual mapping stage...")

    if generate_attention_map:
        update_progress(28, 1, "Running Page X-Ray scan...")

        try:
            xray_url = scraped_data.get("final_url") or target_url
            attention_map_data = capture_attention_map_data(
                xray_url,
                viewport_width=attention_viewport_width,
                viewport_height=attention_viewport_height,
                full_page=attention_full_page,
                wait_ms=1500,
                max_elements=120,
            )
            details[1] = "Page X-Ray scan completed."
        except Exception as exc:
            visual_map_error = f"capture failed: {type(exc).__name__}: {exc}"
            details[1] = "Page X-Ray scan failed. The audit will continue without the visual map."
    else:
        details[1] = "Page X-Ray generation disabled for this run."

    completed.add(1)
    update_progress(42, 2, "Building deterministic SEO baseline report...")

    scraped_json = _json_dumps(scraped_data)

    completed.add(2)
    update_progress(58, 3, f"Enhancing narrative analysis with model: {OLLAMA_MODEL}...")

    report_dict = cached_audit(scraped_json, options_json)
    audit_report = SEOAuditReport.model_validate(report_dict)
    llm_fallback_used = _looks_like_llm_fallback(audit_report)

    completed.add(3)
    update_progress(74, 4, "Saving completed audit to history...")

    try:
        insert_resp = supabase.table("audits").insert(
            {
                "user_id": st.session_state.uid,
                "url": target_url,
                "json": audit_report.model_dump_json(),
                "scraped_data": scraped_data,
            }
        ).execute()
    except Exception as exc:
        progress_bar.progress(100, text="Audit generated but could not be saved.")
        result_box.error(f"Audit was generated, but could not be saved: {type(exc).__name__}: {exc}")

        with st.expander("Download unsaved report JSON"):
            st.download_button(
                "Download JSON",
                data=audit_report.model_dump_json(indent=2),
                file_name="seo_audit_unsaved.json",
                mime="application/json",
                type="secondary",
            )

        st.stop()

    try:
        if insert_resp.data:
            saved_audit_id = insert_resp.data[0].get("id")
    except Exception:
        saved_audit_id = None

    if saved_audit_id is not None and attention_map_data is not None:
        update_progress(82, 4, "Attaching Page X-Ray Site Map to the saved audit...")

        try:
            save_attention_map_artifact(
                supabase,
                audit_id=str(saved_audit_id),
                user_id=str(st.session_state.uid),
                map_data=attention_map_data,
                map_type="attention_map",
            )
            visual_map_saved = True
        except Exception as exc:
            visual_map_error = f"save failed: {type(exc).__name__}: {exc}"

    completed.add(4)
    update_progress(90, 5, "Final checks...")

    try:
        supabase.table("users").update(
            {"credits": credits - 1}
        ).eq("id", st.session_state.uid).execute()

        st.session_state.credits = credits - 1

    except Exception as exc:
        progress_bar.progress(100, text="Audit saved, but credit update failed.")
        result_box.warning(
            f"Audit was saved, but credit update failed: {type(exc).__name__}. Please refresh your account state."
        )
        st.stop()

    completed.add(5)
    progress_bar.progress(100, text="Audit completed successfully.")
    step_box.html(
        _render_step_list(5, completed, details)
    )

    if saved_audit_id is not None:
        st.session_state.active_audit_id = saved_audit_id
        st.session_state.last_completed_audit_id = saved_audit_id

    tone, message = _completion_message(
        saved_audit_id=str(saved_audit_id) if saved_audit_id is not None else None,
        visual_map_enabled=generate_attention_map,
        visual_map_saved=visual_map_saved,
        visual_map_error=visual_map_error,
        llm_fallback_used=llm_fallback_used,
    )

    result_box.html(
        f"""
        <div class="audit-progress-result">
            <strong>Process complete.</strong><br>
            {message}
        </div>
        """
    )

    if visual_map_error:
        with st.expander("Technical Page X-Ray details", expanded=False):
            st.code(visual_map_error)

    if st.button("Close", use_container_width=True, type="primary"):
        st.rerun()

def auditView():
    st.html(PAGE_CSS)
    supabase = cached_supabase()

    credits = _safe_credits()

    st.title("Start an Audit")
    st.markdown(
        "Enter a website URL below to crawl its tags and generate an AI-assisted SEO action plan. "
        "**Each audit costs 1 credit.**"
    )

    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    raw_url = c1.text_input(
        "Target URL",
        placeholder="https://example.com",
        label_visibility="collapsed",
        icon=":material/link:",
    )

    generate_clicked = c2.button(
        "Generate Audit",
        type="primary",
        disabled=credits <= 0,
        help="Not enough credits." if credits <= 0 else None,
        use_container_width=True,
        icon=":material/settings:",
    )

    st.space("small")

    c3, c4 = st.columns([1.1, 0.9], gap="large")

    with c3:
        with st.container(border=True):
            st.subheader("Advanced Tuning")
            st.markdown(
                """
                <style>
                button[data-baseweb="tab"] {
                    font-size: 24px;
                    margin: 0;
                    width: 100%;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            tab_seo, tab_model, tab_scrape, tab_report = st.tabs(
                ["SEO Context", "Model", "Scrape", "Report Style"]
            )

            with tab_seo:
                focus_keyword = st.text_input(
                    "Primary Focus Keyword",
                    placeholder="e.g., custom mechanical keyboards",
                    help="The audit will evaluate whether this exact keyword is positioned well in metadata, headings, and content.",
                )
                secondary_keywords = st.text_input(
                    "Secondary Keywords",
                    placeholder="e.g., artisan keycaps, mechanical switches",
                    help="Comma-separated terms to evaluate for natural coverage and placement.",
                )
                site_archetype = st.selectbox(
                    "Website Archetype",
                    [
                        "General Corporate / Informational",
                        "E-Commerce / Direct Retail Store",
                        "SaaS / B2B Technology Portal",
                        "Local Business / Regional Services",
                        "Blog / Content Publisher Network",
                    ],
                    help="Changes how the report weighs conversion, schema, E-E-A-T, and content expectations.",
                )
                audit_rigor = st.selectbox(
                    "Audit Rigor",
                    [
                        "Standard Optimization Audit",
                        "Hyper-Critical Forensic Check (Strict Grading)",
                        "Lenient Assessment (Core Indexing Infrastructure Only)",
                    ],
                    help="Controls how aggressively the scoring logic penalizes issues.",
                )

            with tab_model:
                m1, m2 = st.columns(2)
                temperature = m1.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.2,
                    step=0.05,
                    help="Lower values produce more consistent report wording.",
                )
                top_p = m2.slider(
                    "Top-p",
                    min_value=0.1,
                    max_value=1.0,
                    value=0.9,
                    step=0.05,
                    help="Nucleus sampling threshold.",
                )

                m3, m4 = st.columns(2)
                max_tokens = m3.select_slider(
                    "Max output tokens",
                    options=[1024, 2048, 3072, 4096, 6144],
                    value=2048,
                    help="2048 is usually enough for the shorter narrative-enhancement prompt.",
                )
                num_ctx = m4.select_slider(
                    "Context window (num_ctx)",
                    options=[4096, 8192, 16384, 32768],
                    value=8192,
                    help="How much prompt and scraped data the model can hold.",
                )

                seed = st.number_input(
                    "Seed (optional)",
                    min_value=0,
                    value=0,
                    step=1,
                    help="Set a positive integer for reproducible wording. Leave at 0 to omit.",
                )
                model_timeout = st.select_slider(
                    "Model analysis timeout (s)",
                    options=[60, 120, 180, 240, 300, 360, 420],
                    value=240,
                    help="The deterministic baseline protects the audit if the model times out or fails.",
                )

            with tab_scrape:
                scrape_timeout = st.select_slider(
                    "Web scraping timeout (s)",
                    options=[30, 45, 60, 90, 120, 180],
                    value=60,
                )
                body_snippet_chars = st.select_slider(
                    "Body snippet length",
                    options=[1500, 2000, 3000, 4000, 5000, 6000],
                    value=3000,
                    help="Characters of page body text sent to the model. Lower values are faster and more stable.",
                )
                force_fresh_run = st.checkbox(
                    "Force fresh scrape and model run",
                    value=False,
                    help="Bypasses the 5-minute cache for this run.",
                )

                generate_attention_map = st.checkbox(
                    "Generate Page X-Ray attention map",
                    value=True,
                    help="Captures a screenshot and stores an interactive visual attention overlay with this audit.",
                )

                attention_full_page = st.checkbox(
                    "Full-page attention map",
                    value=False,
                    help="Full-page maps are more useful but slower and larger. Viewport maps are faster.",
                    disabled=not generate_attention_map,
                )

                attention_viewport_width = st.select_slider(
                    "Attention map viewport width",
                    options=[390, 768, 1024, 1280, 1440, 1920],
                    value=1440,
                    disabled=not generate_attention_map or attention_full_page,
                )

                attention_viewport_height = st.select_slider(
                    "Attention map viewport height",
                    options=[800, 1000, 1200, 1600],
                    value=1200,
                    disabled=not generate_attention_map or attention_full_page,
                )

            with tab_report:
                output_language = st.selectbox(
                    "Output language",
                    ["English", "Match site language", "Spanish", "French", "German", "Turkish", "Japanese"],
                    help="Language used for narrative analysis and action items.",
                )
                analysis_depth = st.selectbox(
                    "Analysis depth",
                    ["Brief", "Standard", "Exhaustive"],
                    index=1,
                    help="Controls how detailed each analysis section should be.",
                )
                report_tone = st.selectbox(
                    "Report tone",
                    ["Technical", "Executive Summary", "Developer-Focused"],
                    help="Adjusts the writing style of critiques and recommendations.",
                )

    with c4:
        with st.container(border=True):
            st.subheader("Execution Profile")
            st.metric("Available Credits", credits)
            st.write(f"Current model: `{OLLAMA_MODEL}`")

    if not generate_clicked:
        return

    is_valid, target_url = _validate_url(raw_url)
    if not is_valid:
        st.warning("Please enter a valid URL, e.g. https://example.com")
        st.stop()

    tuning_options = {
        "focus_keyword": focus_keyword.strip(),
        "secondary_keywords": secondary_keywords.strip(),
        "site_archetype": site_archetype,
        "audit_rigor": audit_rigor,
        "scrape_timeout": scrape_timeout,
        "model_timeout": model_timeout,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "seed": seed if seed > 0 else None,
        "num_ctx": num_ctx,
        "body_snippet_chars": body_snippet_chars,
        "output_language": output_language,
        "analysis_depth": analysis_depth,
        "report_tone": report_tone,
    }

    if force_fresh_run:
        tuning_options["_cache_bust"] = time.time()

    options_json = _json_dumps(tuning_options)

    _audit_progress_dialog(
        supabase=supabase,
        target_url=target_url,
        options_json=options_json,
        credits=credits,
        generate_attention_map=generate_attention_map,
        attention_full_page=attention_full_page,
        attention_viewport_width=attention_viewport_width,
        attention_viewport_height=attention_viewport_height,
    )

    return