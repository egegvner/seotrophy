import streamlit as st
import dotenv
import os
from supabase import create_client
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import base64
import pandas as pd
import plotly.io as pio
from playwright.sync_api import sync_playwright
import re
import tempfile

import base64
import html
from io import BytesIO
from typing import Any

import pandas as pd
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components


def _clear_query_params() -> None:
    for key in list(st.query_params.keys()):
        del st.query_params[key]


def _build_receipt_pdf(purchase_data: dict, session_id: str, event_id: str | None) -> bytes:
    def _money(amount_cents: int | None, currency: str | None) -> str:
        amount_cents = amount_cents or 0
        currency = (currency or "usd").upper()
        return f"{amount_cents / 100:.2f} {currency}"

    amount_total = purchase_data.get("amount_total", 0)
    currency = purchase_data.get("currency", "usd")
    created_at = purchase_data.get("created_at", "N/A")
    plan_title = purchase_data.get("plan_title", "N/A")
    credits_added = purchase_data.get("credits_added", 0)
    customer_email = purchase_data.get("customer_email", "N/A")

    html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          @page {{
            size: A4;
            margin: 18mm;
          }}

          body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #111827;
            margin: 0;
            padding: 0;
            background: #ffffff;
          }}

          .page {{
            width: 100%;
          }}

          .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 1px solid #d1d5db;
          }}

          .brand {{
            font-size: 18px;
            font-weight: 700;
            color: #111827;
            margin: 0 0 4px 0;
          }}

          .subtitle {{
            font-size: 12px;
            color: #6b7280;
            margin: 0;
          }}

          .status {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #166534;
            border: 1px solid #bbf7d0;
            background: #f0fdf4;
            padding: 6px 10px;
          }}

          .section {{
            margin-bottom: 22px;
          }}

          .section-title {{
            font-size: 13px;
            font-weight: 700;
            color: #111827;
            margin: 0 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}

          .grid {{
            display: table;
            width: 100%;
            border-collapse: collapse;
          }}

          .grid-row {{
            display: table-row;
          }}

          .grid-cell {{
            display: table-cell;
            width: 50%;
            padding: 0 8px 8px 0;
            vertical-align: top;
          }}

          .box {{
            border: 1px solid #d1d5db;
            padding: 12px 14px;
            min-height: 64px;
          }}

          .label {{
            font-size: 11px;
            color: #6b7280;
            margin: 0 0 6px 0;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}

          .value {{
            font-size: 14px;
            font-weight: 600;
            color: #111827;
            margin: 0;
            line-height: 1.45;
            word-break: break-word;
          }}

          table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 6px;
          }}

          th, td {{
            border: 1px solid #d1d5db;
            padding: 10px 12px;
            text-align: left;
            font-size: 13px;
          }}

          th {{
            background: #f9fafb;
            font-weight: 700;
            width: 32%;
          }}

          .note {{
            font-size: 12px;
            color: #4b5563;
            line-height: 1.5;
            border-top: 1px solid #d1d5db;
            padding-top: 12px;
            margin-top: 18px;
          }}

          .footer {{
            margin-top: 18px;
            padding-top: 10px;
            border-top: 1px solid #d1d5db;
            font-size: 11px;
            color: #6b7280;
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <div class="header">
            <div>
              <p class="brand">SEO Audit Tool</p>
              <p class="subtitle">Payment Receipt</p>
            </div>
            <div class="status">Paid</div>
          </div>

          <div class="section">
            <p class="section-title">Purchase summary</p>
            <div class="grid">
              <div class="grid-row">
                <div class="grid-cell">
                  <div class="box">
                    <p class="label">Package</p>
                    <p class="value">{plan_title}</p>
                  </div>
                </div>
                <div class="grid-cell">
                  <div class="box">
                    <p class="label">Credits added</p>
                    <p class="value">+{credits_added}</p>
                  </div>
                </div>
              </div>
              <div class="grid-row">
                <div class="grid-cell">
                  <div class="box">
                    <p class="label">Amount paid</p>
                    <p class="value">{_money(amount_total, currency)}</p>
                  </div>
                </div>
                <div class="grid-cell">
                  <div class="box">
                    <p class="label">Payment method</p>
                    <p class="value">Stripe Checkout</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="section">
            <p class="section-title">Transaction details</p>
            <table>
              <tr>
                <th>Transaction ID</th>
                <td>{event_id or "N/A"}</td>
              </tr>
              <tr>
                <th>Checkout session</th>
                <td>{session_id or "N/A"}</td>
              </tr>
              <tr>
                <th>Customer email</th>
                <td>{customer_email}</td>
              </tr>
              <tr>
                <th>Processed at</th>
                <td>{created_at}</td>
              </tr>
            </table>
          </div>

          <div class="note">
            This receipt confirms that the payment was completed successfully and the credits were added to the user account.
            Keep this document for your records.
          </div>

          <div class="footer">
            Generated by SEO Audit Tool
          </div>
        </div>
      </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 960, "height": 1200}, device_scale_factor=2)
        page.set_content(html, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "16mm", "right": "16mm", "bottom": "16mm", "left": "16mm"},
        )
        browser.close()

    return pdf_bytes

def _qp(name: str, default: str = "") -> str:
    value = st.query_params.get(name, default)

    if isinstance(value, list):
        return value[0] if value else default

    if value is None:
        return default

    return str(value)

def validate_password(password: str) -> tuple[bool, str]:
    """
    Returns:
        (True, "") if password is valid
        (False, message) if password is invalid
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password is too long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."

    if not re.search(r"[^\w\s]", password):
        return False, "Password must contain at least one special character."

    if re.search(r"\s", password):
        return False, "Password must not contain spaces."

    return True, ""


@st.cache_resource
def get_supabase():
    dotenv.load_dotenv()
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )


@st.cache_resource
def cached_supabase():
    return get_supabase()


@st.cache_data(ttl=10, show_spinner=False)
def get_user_audits(uid):
    supabase = cached_supabase()
    return (
        supabase
        .table("audits")
        .select("id,url,created_at,json,is_archived")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def get_user_audits_new(uid):
    supabase = cached_supabase()
    return (
        supabase
        .table("audits")
        .select("id,url,created_at,json,is_archived")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .execute()
        .data
    )


@st.cache_data(ttl=60, show_spinner=False)
def get_user_total_purchased_credits(uid: str) -> int:
    supabase = cached_supabase()
    response = (
        supabase
        .table("stripe_events")
        .select("credits_added")
        .eq("user_id", uid)
        .execute()
    )
    
    total_purchased = sum(item.get("credits_added", 0) for item in response.data)
    
    return max(20, total_purchased)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_site_title(url):
    return get_site_title(url)


@st.cache_data(ttl=86400, show_spinner=False)
def cached_favicon(url):
    return get_favicon_url(url)


@st.cache_data(ttl=30, show_spinner=False)
def get_credit_history_timeline(uid: str) -> pd.DataFrame:
    supabase = cached_supabase()
    
    purchases_res = (
        supabase.table("stripe_events")
        .select("created_at, credits_added, plan_title")
        .eq("user_id", uid)
        .execute()
    )
    
    usages_res = (
        supabase.table("audits")
        .select("created_at, url")
        .eq("user_id", uid)
        .execute()
    )
    
    events = []
    initial_credits = 5 
    
    for p in purchases_res.data:
        events.append({
            "timestamp": pd.to_datetime(p["created_at"]),
            "change": p["credits_added"],
            "event_type": "Purchase",
            "meta": f"Purchased Pack: {p['plan_title']}"
        })
        
    for u in usages_res.data:
        events.append({
            "timestamp": pd.to_datetime(u["created_at"]),
            "change": -1,
            "event_type": "Audit Usage",
            "meta": f"Audited Target: {u['url']}"
        })
        
    if not events:
        return pd.DataFrame()
        
    df = pd.DataFrame(events).sort_values(by="timestamp").reset_index(drop=True)
    df["balance"] = initial_credits + df["change"].cumsum()
    
    return df


import plotly.graph_objects as go
import streamlit as st

def render_credit_analytics_chart(df):
    if df.empty:
        st.info("Insufficient system logs to populate asset timeline visualizer.")
        return

    purchases = df[df["event_type"] == "Purchase"]
    usages = df[df["event_type"] == "Audit Usage"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["balance"],
        mode="lines",
        line=dict(color="#6366f1", width=3, shape="hv"),
        name="Credit Balance",
        hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=purchases["timestamp"],
        y=purchases["balance"],
        mode="markers",
        marker=dict(
            color="#22c55e",
            size=11,
            symbol="circle",
            line=dict(color="#ffffff", width=2)
        ),
        name="Purchases",
        customdata=purchases["meta"],
        hovertemplate="<b>🟢 Credit Top-up</b><br><b>Time:</b> %{x}<br><b>Balance:</b> %{y} Credits<br><b>%{customdata}</b><extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=usages["timestamp"],
        y=usages["balance"],
        mode="markers",
        marker=dict(
            color="#ef4444", 
            size=8,
            symbol="circle",
            line=dict(color="#ffffff", width=1)
        ),
        name="Usage Deductions",
        customdata=usages["meta"],
        hovertemplate="<b>🔴 Credit Used</b><br><b>Time:</b> %{x}<br><b>Balance:</b> %{y} Credits<br><b>%{customdata}</b><extra></extra>"
    ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=10, b=10),
        height=320,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="closest",
        xaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            linecolor="#cbd5e1",
            tickfont=dict(color="#64748b", size=11)
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#f1f5f9",
            linecolor="#cbd5e1",
            tickfont=dict(color="#64748b", size=11),
            zeroline=False
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, height=450)


def get_favicon_url(website_url):
    try:
        response = requests.get(
            website_url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("link"):
            rel = link.get("rel")

            if rel and any("icon" in r.lower() for r in rel):
                href = link.get("href")

                if href:
                    return urljoin(website_url, href)

        return urljoin(website_url, "/favicon.ico")

    except Exception:
        return None


def get_site_title(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )

        soup = BeautifulSoup(response.text, "html.parser")

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        if soup.title and soup.title.string:
            return soup.title.string.strip()

        return None

    except Exception:
        return None
    

def time_ago(timestamp_str):
    timestamp = datetime.fromisoformat(timestamp_str)

    now = datetime.now(timezone.utc)
    diff = now - timestamp

    seconds = int(diff.total_seconds())

    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''} ago"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"

    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"



def _img_to_base64(fig) -> str:
    png_bytes = pio.to_image(fig, format="png", scale=2)
    return base64.b64encode(png_bytes).decode("utf-8")


def _safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _split_action_items(markdown_text: str):
    if not markdown_text:
        return []
    items = []
    for line in markdown_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        items.append(line)
    return items


import html
import textwrap
from playwright.sync_api import sync_playwright


def _safe_text(value, fallback="N/A"):
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _escape(value, fallback="N/A"):
    return html.escape(_safe_text(value, fallback))


def _yes_no(value):
    return "Yes" if bool(value) else "No"


def _build_kv_row(label: str, value: str) -> str:
    return f"""
        <tr>
            <th>{_escape(label)}</th>
            <td>{_escape(value)}</td>
        </tr>
    """


def _build_audit_pdf(report, scraped: dict, page_url: str, site_title: str, audit_id: str) -> bytes:
    """
    Build a minimal corporate-style PDF for an SEO audit.
    Expects:
        report: SEOAuditReport object
        scraped: dict from scraped_data
        page_url: audited URL
        site_title: cached site title or fallback title
        audit_id: internal audit identifier
    """

    # Core values
    overall_score = getattr(report, "overall_score", 0)
    category_scores = getattr(report, "category_scores", {}) or {}

    # Basic metrics
    word_count = scraped.get("word_count", 0)
    total_images = scraped.get("total_images", 0)
    images_missing_alt = scraped.get("images_missing_alt", 0)
    internal_links = scraped.get("internal_links", 0)
    external_links = scraped.get("external_links", 0)
    response_time_sec = scraped.get("response_time_sec", 0)
    page_size_kb = scraped.get("page_size_kb", 0)

    # Technical values
    canonical_url = scraped.get("canonical_url", "Missing")
    meta_robots = scraped.get("meta_robots", "None")
    viewport_string = scraped.get("viewport_string", "Missing")
    is_https = _yes_no(scraped.get("is_https"))
    mobile_viewport = _yes_no(scraped.get("has_mobile_viewport"))
    query_strings = _yes_no(scraped.get("has_query_strings"))

    # Trust values
    has_about_page = _yes_no(scraped.get("has_about_page"))
    has_contact_page = _yes_no(scraped.get("has_contact_page"))
    has_privacy_policy = _yes_no(scraped.get("has_privacy_policy"))
    has_faq_section = _yes_no(scraped.get("has_faq_section"))
    has_breadcrumbs = _yes_no(scraped.get("has_breadcrumbs"))
    trust_signals = _yes_no(scraped.get("trust_signal_presence"))
    cta_presence = _yes_no(scraped.get("cta_presence"))

    # Schema values
    schema_count = scraped.get("schema_count", 0)
    schema_validity = scraped.get("schema_validity", "Unknown")
    schema_types = scraped.get("detected_schema_types", ["None Detected"])
    schema_types_text = ", ".join(map(str, schema_types)) if schema_types else "None Detected"

    # Analysis text
    action_items = getattr(report, "action_item_markdown", "") or ""

    html_content = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          @page {{
            size: A4;
            margin: 18mm;
          }}

          body {{
            font-family: Arial, Helvetica, sans-serif;
            color: #111827;
            margin: 0;
            padding: 0;
            background: #ffffff;
            font-size: 12px;
            line-height: 1.45;
          }}

          .page {{
            width: 100%;
          }}

          .header {{
            border-bottom: 1px solid #d1d5db;
            padding-bottom: 10px;
            margin-bottom: 18px;
          }}

          .title-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
          }}

          .title-block h1 {{
            margin: 0;
            font-size: 20px;
            font-weight: 700;
            color: #111827;
          }}

          .title-block .subtitle {{
            margin: 4px 0 0 0;
            color: #6b7280;
            font-size: 11px;
          }}

          .meta-row {{
            margin-top: 10px;
            color: #6b7280;
            font-size: 11px;
          }}

          .badge {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #1f2937;
            background: #f3f4f6;
            border: 1px solid #d1d5db;
            padding: 6px 10px;
            white-space: nowrap;
          }}

          .section {{
            margin-bottom: 18px;
          }}

          .section-title {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #111827;
            margin: 0 0 8px 0;
          }}

          .summary-box {{
            border: 1px solid #d1d5db;
            padding: 12px;
            background: #fafafa;
          }}

          .summary-text {{
            margin: 0;
            white-space: pre-wrap;
            color: #111827;
          }}

          .grid {{
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
          }}

          .grid td {{
            width: 50%;
            vertical-align: top;
            padding: 0 8px 8px 0;
          }}

          .metric-box {{
            border: 1px solid #d1d5db;
            padding: 10px 12px;
            min-height: 56px;
          }}

          .metric-label {{
            margin: 0 0 5px 0;
            color: #6b7280;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }}

          .metric-value {{
            margin: 0;
            font-size: 14px;
            font-weight: 700;
            color: #111827;
          }}

          table.data-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 4px;
          }}

          table.data-table th,
          table.data-table td {{
            border: 1px solid #d1d5db;
            padding: 8px 10px;
            text-align: left;
            vertical-align: top;
            font-size: 11px;
          }}

          table.data-table th {{
            background: #f9fafb;
            font-weight: 700;
            width: 36%;
          }}

          .analysis {{
            border: 1px solid #d1d5db;
            padding: 10px 12px;
            background: #ffffff;
            white-space: pre-wrap;
            font-size: 11px;
            color: #111827;
          }}

          .footer {{
            border-top: 1px solid #d1d5db;
            margin-top: 18px;
            padding-top: 10px;
            font-size: 10px;
            color: #6b7280;
          }}

          .small {{
            font-size: 10px;
            color: #6b7280;
          }}
        </style>
      </head>
      <body>
        <div class="page">

          <div class="header">
            <div class="title-row">
              <div class="title-block">
                <h1>SEO Audit Report</h1>
                <p class="subtitle">{_escape(site_title, "SEO Audit Report")}</p>
                <div class="meta-row">
                  Audit ID: {_escape(audit_id)}<br/>
                  URL: {_escape(page_url)}<br/>
                </div>
              </div>
              <div class="badge">Overall Score: {int(overall_score)}</div>
            </div>
          </div>

          <div class="section">
            <p class="section-title">Executive Summary</p>
            <div class="summary-box">
              <p class="summary-text">
This report summarizes the current SEO, content, technical, trust, and structured data state of the audited page. The score and findings are based on the parsed audit output and scraped page data.
              </p>
            </div>
          </div>

          <div class="section">
            <p class="section-title">Key Metrics</p>
            <table class="grid">
              <tr>
                <td><div class="metric-box"><p class="metric-label">Word Count</p><p class="metric-value">{int(word_count):,}</p></div></td>
                <td><div class="metric-box"><p class="metric-label">Total Images</p><p class="metric-value">{int(total_images)}</p></div></td>
              </tr>
              <tr>
                <td><div class="metric-box"><p class="metric-label">Missing Alt Tags</p><p class="metric-value">{int(images_missing_alt)}</p></div></td>
                <td><div class="metric-box"><p class="metric-label">Internal Links</p><p class="metric-value">{int(internal_links)}</p></div></td>
              </tr>
              <tr>
                <td><div class="metric-box"><p class="metric-label">External Links</p><p class="metric-value">{int(external_links)}</p></div></td>
                <td><div class="metric-box"><p class="metric-label">Response Time</p><p class="metric-value">{float(response_time_sec):.3f}s</p></div></td>
              </tr>
              <tr>
                <td><div class="metric-box"><p class="metric-label">Page Size</p><p class="metric-value">{float(page_size_kb):.1f} KB</p></div></td>
                <td><div class="metric-box"><p class="metric-label">HTTPS</p><p class="metric-value">{_escape(is_https)}</p></div></td>
              </tr>
            </table>
          </div>

          <div class="section">
            <p class="section-title">Category Scores</p>
            <table class="data-table">
              <tr><th>Category</th><th>Score</th></tr>
              {''.join(f'<tr><td>{_escape(k)}</td><td>{int(v)}</td></tr>' for k, v in category_scores.items())}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Metadata and Directives</p>
            <table class="data-table">
              {_build_kv_row("Title", getattr(report, "suggested_title", "") or "N/A")}
              {_build_kv_row("Meta Description", getattr(report, "suggested_meta", "") or "N/A")}
              {_build_kv_row("Canonical URL", canonical_url)}
              {_build_kv_row("Meta Robots", meta_robots)}
              {_build_kv_row("Viewport", viewport_string)}
              {_build_kv_row("Mobile Viewport", mobile_viewport)}
              {_build_kv_row("Query Strings Present", query_strings)}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Content and Structure</p>
            <table class="data-table">
              {_build_kv_row("Content Depth", getattr(report, "content_depth_analysis", "") or "N/A")}
              {_build_kv_row("Heading Hierarchy", getattr(report, "heading_hierarchy_analysis", "") or "N/A")}
              {_build_kv_row("Content Quality", getattr(report, "content_quality_analysis", "") or "N/A")}
              {_build_kv_row("Word Count", f"{int(word_count):,}")}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Technical</p>
            <table class="data-table">
              {_build_kv_row("Image Accessibility", getattr(report, "image_alt_analysis", "") or "N/A")}
              {_build_kv_row("Link Strategy", getattr(report, "link_strategy_analysis", "") or "N/A")}
              {_build_kv_row("Performance & Security", getattr(report, "security_performance_analysis", "") or "N/A")}
              {_build_kv_row("URL Structure", getattr(report, "url_structure_analysis", "") or "N/A")}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Trust and Authority</p>
            <table class="data-table">
              {_build_kv_row("E-E-A-T Analysis", getattr(report, "eeat_authority_analysis", "") or "N/A")}
              {_build_kv_row("Trust Signals", trust_signals)}
              {_build_kv_row("CTA Present", cta_presence)}
              {_build_kv_row("Privacy Policy", has_privacy_policy)}
              {_build_kv_row("Contact Page", has_contact_page)}
              {_build_kv_row("About Page", has_about_page)}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Schema and Indexing</p>
            <table class="data-table">
              {_build_kv_row("Structured Data Analysis", getattr(report, "schema_structured_data_analysis", "") or "N/A")}
              {_build_kv_row("Indexing Directives Analysis", getattr(report, "indexing_directives_analysis", "") or "N/A")}
              {_build_kv_row("Schema Count", str(int(schema_count)))}
              {_build_kv_row("Schema Validity", schema_validity)}
              {_build_kv_row("Detected Schema Types", schema_types_text)}
            </table>
          </div>

          <div class="section">
            <p class="section-title">Priority Action Plan</p>
            <div class="analysis">{_escape(action_items or "No action items were generated.")}</div>
          </div>

          <div class="footer">
            Generated by SEO Audit Tool
          </div>
        </div>
      </body>
    </html>
    """

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1600}, device_scale_factor=2)
        page.set_content(html_content, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "16mm", "right": "16mm", "bottom": "16mm", "left": "16mm"},
        )
        browser.close()

    return pdf_bytes

ATTENTION_SELECTORS = [
    "h1",
    "h2",
    "h3",
    "a",
    "button",
    "img",
    "form",
    "input",
    "textarea",
    "select",
    "[role='button']",
    "[role='link']",
    "[aria-label]",
    "nav",
    "header",
    "main",
    "section",
    "article",
    "footer",
]


CTA_KEYWORDS = [
    "buy",
    "start",
    "get started",
    "sign up",
    "subscribe",
    "pricing",
    "demo",
    "contact",
    "book",
    "checkout",
    "try",
    "download",
    "learn more",
]


def _normalize_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("URL is empty.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    host = urlparse(url).netloc
    if "." not in host:
        raise ValueError("Invalid URL.")
    return url


def _score_element(element: dict, viewport_height: int) -> int:
    tag = element.get("tag", "").lower()
    text = (element.get("text") or "").lower()
    y = float(element.get("y", 0))
    width = float(element.get("width", 0))
    height = float(element.get("height", 0))
    area = width * height

    score = 20

    # Above-the-fold boost
    if y < viewport_height * 0.35:
        score += 35
    elif y < viewport_height * 0.75:
        score += 20
    elif y < viewport_height * 1.5:
        score += 10
    else:
        score -= 5

    # Tag importance
    if tag == "h1":
        score += 30
    elif tag == "h2":
        score += 20
    elif tag == "h3":
        score += 10
    elif tag in {"button", "a"}:
        score += 18
    elif tag in {"form", "input", "textarea", "select"}:
        score += 16
    elif tag == "img":
        score += 10
    elif tag in {"nav", "header"}:
        score += 8
    elif tag == "footer":
        score -= 12

    # CTA wording boost
    if any(keyword in text for keyword in CTA_KEYWORDS):
        score += 25

    # Visual size boost
    if area > 120_000:
        score += 18
    elif area > 50_000:
        score += 10
    elif area < 600:
        score -= 10

    # Avoid huge full-page containers dominating the map
    if tag in {"section", "main", "article"} and area > 400_000:
        score -= 15

    return max(1, min(100, int(score)))


def capture_attention_map_data(
    url: str,
    viewport_width: int = 1440,
    viewport_height: int = 1200,
    full_page: bool = False,
    wait_ms: int = 1500,
    max_elements: int = 200,
) -> dict:
    """
    Captures a screenshot and visible element boxes for an attention-map simulator.
    This version is safer for Streamlit/VPS deployment:
    - does not require networkidle to succeed
    - ignores HTTPS certificate errors
    - uses Chromium launch flags that are commonly required inside Linux servers/containers
    - always closes browser/context cleanly
    """
    target_url = _normalize_url(url)

    browser = None
    context = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox",
                ],
            )

            context = browser.new_context(
                viewport={"width": int(viewport_width), "height": int(viewport_height)},
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            # Some pages keep analytics/websocket requests open forever.
            # networkidle therefore fails on many real sites. Use domcontentloaded
            # as the required milestone, then try networkidle only as a soft wait.
            page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_load_state("networkidle", timeout=7000)
            except Exception:
                pass

            page.wait_for_timeout(int(wait_ms))

            screenshot_bytes = page.screenshot(full_page=bool(full_page), type="png")
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            elements = page.evaluate(
                """
                (selectors) => {
                    const nodes = Array.from(document.querySelectorAll(selectors.join(",")));

                    return nodes.map((el) => {
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        const text = (el.innerText || el.getAttribute("aria-label") || el.alt || "").trim();

                        return {
                            tag: el.tagName.toLowerCase(),
                            text: text.slice(0, 120),
                            href: el.getAttribute("href") || "",
                            aria_label: el.getAttribute("aria-label") || "",
                            role: el.getAttribute("role") || "",
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height,
                            visible: (
                                rect.width > 0 &&
                                rect.height > 0 &&
                                style.visibility !== "hidden" &&
                                style.display !== "none" &&
                                parseFloat(style.opacity || "1") > 0
                            )
                        };
                    }).filter((item) => item.visible);
                }
                """,
                ATTENTION_SELECTORS,
            )

    finally:
        try:
            if context is not None:
                context.close()
        except Exception:
            pass
        try:
            if browser is not None:
                browser.close()
        except Exception:
            pass

    filtered = []
    for item in elements:
        if item["width"] < 8 or item["height"] < 8:
            continue

        score = _score_element(item, viewport_height)
        item["attention_score"] = score

        if score >= 75:
            item["attention_level"] = "High"
        elif score >= 45:
            item["attention_level"] = "Medium"
        else:
            item["attention_level"] = "Low"

        filtered.append(item)

    filtered.sort(key=lambda x: x["attention_score"], reverse=True)

    return {
        "url": target_url,
        "viewport_width": viewport_width,
        "viewport_height": viewport_height,
        "full_page": full_page,
        "screenshot_b64": screenshot_b64,
        "elements": filtered[:max_elements],
    }

import base64
import json
from io import BytesIO
from PIL import Image


VISUAL_MAP_BUCKET = "audit-maps"


def _image_size_from_b64(screenshot_b64: str) -> tuple[int, int]:
    image_bytes = base64.b64decode(screenshot_b64)
    image = Image.open(BytesIO(image_bytes))
    return image.size


def _summarize_attention_elements(elements: list[dict]) -> dict:
    high = sum(1 for e in elements if e.get("attention_level") == "High")
    medium = sum(1 for e in elements if e.get("attention_level") == "Medium")
    low = sum(1 for e in elements if e.get("attention_level") == "Low")

    top_elements = []
    for e in elements[:10]:
        top_elements.append(
            {
                "tag": e.get("tag", ""),
                "text": (e.get("text") or e.get("aria_label") or e.get("href") or "")[:140],
                "attention_score": e.get("attention_score", 0),
                "attention_level": e.get("attention_level", "Unknown"),
            }
        )

    return {
        "total_regions": len(elements),
        "high_attention_regions": high,
        "medium_attention_regions": medium,
        "low_attention_regions": low,
        "top_elements": top_elements,
    }


def save_attention_map_artifact(
    supabase,
    *,
    audit_id: str,
    user_id: str,
    map_data: dict,
    map_type: str = "attention_map",
) -> dict:
    """
    Stores screenshot in Supabase Storage and metadata/overlays in audit_visual_maps.

    Important implementation detail:
    some supabase-py/storage versions are more reliable when uploading from a
    temporary file path instead of raw bytes. This avoids silent storage upload
    failures on local/VPS environments.
    """
    screenshot_b64 = map_data.get("screenshot_b64", "")
    if not screenshot_b64:
        raise ValueError("Attention map data does not contain screenshot_b64.")

    screenshot_bytes = base64.b64decode(screenshot_b64)
    image_width, image_height = _image_size_from_b64(screenshot_b64)

    viewport_width = int(map_data.get("viewport_width", 0) or 0)
    viewport_height = int(map_data.get("viewport_height", 0) or 0)
    full_page = bool(map_data.get("full_page", False))

    screenshot_path = (
        f"{user_id}/{audit_id}/{map_type}_"
        f"{viewport_width}x{viewport_height}_"
        f"{'full' if full_page else 'viewport'}.png"
    )

    # Upload screenshot to private Supabase Storage bucket.
    # Remove first to avoid object-exists errors if the same audit/map is retried.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(screenshot_bytes)
            tmp_path = tmp.name

        try:
            supabase.storage.from_(VISUAL_MAP_BUCKET).remove([screenshot_path])
        except Exception:
            pass

        supabase.storage.from_(VISUAL_MAP_BUCKET).upload(
            path=screenshot_path,
            file=tmp_path,
            file_options={"content-type": "image/png"},
        )
    except Exception as exc:
        raise RuntimeError(
            f"Supabase Storage upload failed for bucket '{VISUAL_MAP_BUCKET}' and path '{screenshot_path}': "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    elements = map_data.get("elements", [])
    summary = _summarize_attention_elements(elements)

    row = {
        "audit_id": audit_id,
        "user_id": user_id,
        "map_type": map_type,
        "url": map_data.get("url", ""),
        "viewport_width": viewport_width,
        "viewport_height": viewport_height,
        "full_page": full_page,
        "screenshot_bucket": VISUAL_MAP_BUCKET,
        "screenshot_path": screenshot_path,
        "image_width": image_width,
        "image_height": image_height,
        "elements": elements,
        "summary": summary,
        "settings": {
            "max_elements": len(elements),
            "simulated": True,
            "model": "deterministic_attention_scoring_v1",
        },
    }

    try:
        resp = supabase.table("audit_visual_maps").insert(row).execute()
    except Exception as exc:
        raise RuntimeError(
            f"audit_visual_maps insert failed: {type(exc).__name__}: {exc}"
        ) from exc

    if not resp.data:
        raise RuntimeError("Supabase did not return inserted visual map row. Check table permissions/RLS.")

    return resp.data[0]


def load_audit_visual_maps(supabase, audit_id: str) -> list[dict]:
    resp = (
        supabase.table("audit_visual_maps")
        .select("*")
        .eq("audit_id", audit_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def get_signed_screenshot_url(
    supabase,
    screenshot_path: str,
    expires_in: int = 3600,
    bucket: str = VISUAL_MAP_BUCKET,
) -> str:
    signed = supabase.storage.from_(bucket).create_signed_url(
        screenshot_path,
        expires_in,
    )

    if isinstance(signed, dict):
        return signed.get("signedURL") or signed.get("signedUrl") or ""

    return ""

def _overlay_color(score: int) -> tuple[str, str]:
    """Return fill and border colors for an attention score."""
    if score >= 75:
        return "rgba(239, 68, 68, 0.34)", "rgba(185, 28, 28, 0.95)"
    if score >= 45:
        return "rgba(245, 158, 11, 0.28)", "rgba(180, 83, 9, 0.90)"
    return "rgba(59, 130, 246, 0.20)", "rgba(37, 99, 235, 0.80)"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _limit_elements(data: dict, max_regions: int, min_score: int) -> dict:
    """Return a shallow copy of capture data with filtered overlay elements."""
    filtered = []
    for element in data.get("elements", []):
        score = _safe_int(element.get("attention_score"), 0)
        if score >= min_score:
            filtered.append(element)

    filtered.sort(key=lambda e: _safe_int(e.get("attention_score"), 0), reverse=True)

    limited = dict(data)
    limited["elements"] = filtered[:max_regions]
    return limited


def _image_size_from_b64(screenshot_b64: str) -> tuple[int, int]:
    screenshot_bytes = base64.b64decode(screenshot_b64)
    image = Image.open(BytesIO(screenshot_bytes))
    return image.size


# -----------------------------------------------------------------------------
# HTML screenshot overlay renderer
# -----------------------------------------------------------------------------
def render_attention_map_html(
    data: dict,
    width_percent: int = 90,
    max_visible_height: int = 900,
    show_score_badges: bool = True,
) -> None:
    """
    Render a screenshot at x% of the parent width with percentage-based overlays.

    Why this renderer is used instead of Plotly for full-page screenshots:
    - Full-page screenshots are often very tall.
    - Plotly's aspect-ratio locking makes them visually narrow and awkward.
    - HTML can scale the screenshot width naturally and keep a vertical scroll area.
    - Overlay boxes are expressed as percentages, so they remain aligned when resized.
    """
    screenshot_b64 = data.get("screenshot_b64", "")
    if not screenshot_b64:
        st.warning("No screenshot was returned by the capture engine.")
        return

    natural_width, natural_height = _image_size_from_b64(screenshot_b64)
    if natural_width <= 0 or natural_height <= 0:
        st.warning("The screenshot dimensions could not be detected.")
        return

    width_percent = max(30, min(100, int(width_percent)))
    max_visible_height = max(400, min(1800, int(max_visible_height)))

    boxes_html: list[str] = []

    # SMART FIX: Sort elements by physical area (largest to smallest) 
    # so that smaller nested boxes are rendered on top and can be hovered.
    sorted_elements = sorted(
        data.get("elements", []),
        key=lambda e: _safe_float(e.get("width"), 0.0) * _safe_float(e.get("height"), 0.0),
        reverse=True
    )

    for idx, element in enumerate(sorted_elements, start=1):
        score = _safe_int(element.get("attention_score"), 0)
        fill, border = _overlay_color(score)

        raw_x = _safe_float(element.get("x"), 0.0)
        raw_y = _safe_float(element.get("y"), 0.0)
        raw_w = _safe_float(element.get("width"), 0.0)
        raw_h = _safe_float(element.get("height"), 0.0)

        # Clip boxes to screenshot boundaries. This prevents offscreen or sticky elements
        # from breaking percentage positioning.
        x0 = _clamp(raw_x, 0, natural_width)
        y0 = _clamp(raw_y, 0, natural_height)
        x1 = _clamp(raw_x + raw_w, 0, natural_width)
        y1 = _clamp(raw_y + raw_h, 0, natural_height)

        box_w = x1 - x0
        box_h = y1 - y0
        if box_w < 4 or box_h < 4:
            continue

        left_pct = (x0 / natural_width) * 100
        top_pct = (y0 / natural_height) * 100
        width_pct = (box_w / natural_width) * 100
        height_pct = (box_h / natural_height) * 100

        tag = html.escape(str(element.get("tag", "element")).upper())
        level = html.escape(str(element.get("attention_level", "Unknown")))
        text = html.escape(
            str(
                element.get("text")
                or element.get("aria_label")
                or element.get("href")
                or "No visible text"
            )[:180]
        )

        tooltip = html.escape(
            f"{tag} | Attention: {score}/100 | {level} | {text}",
            quote=True,
        )

        badge_html = f"<span>{score}</span>" if show_score_badges else ""

        boxes_html.append(
            f"""
            <div
                class="attention-box"
                data-tooltip="{tooltip}"
                style="
                    --box-z: {idx};
                    left: {left_pct:.5f}%;
                    top: {top_pct:.5f}%;
                    width: {width_pct:.5f}%;
                    height: {height_pct:.5f}%;
                    background: {fill};
                    border-color: {border};
                "
            >
                {badge_html}
            </div>
            """
        )

    boxes = "\n".join(boxes_html)

    components.html(
        f"""
        <style>
            :root {{
                --accent: #cb785c;
                --border: #e2e8f0;
                --text: #0f172a;
                --muted: #64748b;
            }}

            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }}

            .attention-outer {{
                width: 100%;
                display: flex;
                justify-content: center;
                align-items: flex-start;
            }}

            .attention-shell {{
                width: {width_percent}%;
                max-height: {max_visible_height}px;
                overflow: auto;
                border: 1px solid var(--border);
                border-radius: 20px;
                background: #f8fafc;
                box-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
            }}

            .attention-stage {{
                position: relative;
                width: 100%;
                aspect-ratio: {natural_width} / {natural_height};
                min-width: 320px;
                line-height: 0;
                background: #ffffff;
            }}

            .attention-stage img {{
                position: absolute;
                inset: 0;
                width: 100%;
                height: 100%;
                object-fit: fill;
                display: block;
                user-select: none;
                -webkit-user-drag: none;
            }}

            .attention-box {{
                position: absolute;
                box-sizing: border-box;
                border: 2px solid;
                border-radius: 7px;
                cursor: pointer;
                transition: transform 0.14s ease, background 0.14s ease, border-color 0.14s ease;
                /* Assign dynamic stacking order based on sorted area rank */
                z-index: var(--box-z, 2);
            }}

            .attention-box:hover {{
                transform: scale(1.01);
                background: rgba(203, 120, 92, 0.42) !important;
                border-color: var(--accent) !important;
                /* Intentionally omitting aggressive z-index overrides here so large boxes don't swallow smaller ones on hover */
            }}

            .attention-box span {{
                position: absolute;
                top: 4px;
                left: 4px;
                padding: 2px 6px;
                border-radius: 999px;
                background: rgba(15, 23, 42, 0.88);
                color: #ffffff;
                font-size: 11px;
                line-height: 1.25;
                font-weight: 700;
                white-space: nowrap;
            }}

            .attention-box::after {{
                content: attr(data-tooltip);
                display: none;
                position: absolute;
                left: 0;
                top: calc(100% + 8px);
                width: max-content;
                max-width: 280px;
                white-space: normal;
                padding: 9px 10px;
                border-radius: 12px;
                background: rgba(15, 23, 42, 0.95);
                color: #ffffff;
                font-size: 12px;
                line-height: 1.35;
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.25);
                z-index: 30;
            }}

            .attention-box:hover::after {{
                display: block;
            }}

            .legend {{
                position: sticky;
                top: 0;
                z-index: 50;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                align-items: center;
                padding: 10px 12px;
                border-bottom: 1px solid var(--border);
                background: rgba(248, 250, 252, 0.92);
                backdrop-filter: blur(10px);
                line-height: 1.2;
            }}

            .legend-item {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                color: var(--muted);
                font-size: 12px;
                font-weight: 600;
            }}

            .legend-dot {{
                width: 10px;
                height: 10px;
                border-radius: 999px;
                display: inline-block;
            }}

            .dot-high {{ background: rgba(239, 68, 68, 0.75); }}
            .dot-medium {{ background: rgba(245, 158, 11, 0.75); }}
            .dot-low {{ background: rgba(59, 130, 246, 0.75); }}
        </style>

        <div class="attention-outer">
            <div class="attention-shell">
                <div class="legend">
                    <span class="legend-item"><span class="legend-dot dot-high"></span>High attention</span>
                    <span class="legend-item"><span class="legend-dot dot-medium"></span>Medium attention</span>
                    <span class="legend-item"><span class="legend-dot dot-low"></span>Low attention</span>
                    <span class="legend-item">Hover regions for details</span>
                </div>

                <div class="attention-stage">
                    <img src="data:image/png;base64,{screenshot_b64}" alt="Attention map screenshot" />
                    {boxes}
                </div>
            </div>
        </div>
        """,
        height=max_visible_height + 24,
        scrolling=False,
    )


# -----------------------------------------------------------------------------
# Streamlit view
# -----------------------------------------------------------------------------
def attentionMapView() -> None:
    st.markdown(
        """
        <style>
        ::selection { background: #cb785c; color: #ffffff; }

        .block-container {
            padding-top: 2.25rem;
            padding-bottom: 4rem;
            max-width: 85%;
        }

        .xray-hero {
            margin-bottom: 1.2rem;
        }

        .xray-hero h1 {
            font-size: 2.15rem;
            font-weight: 760;
            letter-spacing: -0.035em;
            margin-bottom: 0.35rem;
            color: #0f172a;
        }

        .xray-hero p {
            color: #475569;
            font-size: 1rem;
            line-height: 1.65;
            max-width: 850px;
            margin: 0;
        }

        .free-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.7rem;
            border: 1px solid #e2e8f0;
            border-radius: 999px;
            background: #ffffff;
            color: #334155;
            font-size: 0.86rem;
            font-weight: 650;
            margin-bottom: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="xray-hero">
            <div class="free-badge">No credits required</div>
            <h1>Page X-Ray: Attention Map</h1>
            <p>
                Generate a simulated visual attention map from a live webpage screenshot.
                The tool estimates likely attention hotspots using page structure, CTAs,
                headings, links, forms, images, and above-the-fold placement.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    @st.cache_data(ttl=300, show_spinner=False)
    def cached_attention_capture(
        url: str,
        viewport_width: int,
        viewport_height: int,
        full_page: bool,
    ) -> dict:
        return capture_attention_map_data(
            url,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            full_page=full_page,
        )

    with st.container(border=True):
        c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
        target_url = c1.text_input(
            "Target URL",
            placeholder="https://example.com",
            label_visibility="collapsed",
            icon=":material/link:",
        )

        run_btn = c2.button(
            "Generate Map",
            type="primary",
            use_container_width=True,
            icon=":material/visibility:",
        )

        with st.expander("Advanced capture and display settings", expanded=False):
            a1, a2, a3 = st.columns(3)
            viewport_width = a1.select_slider(
                "Viewport width",
                options=[390, 768, 1024, 1280, 1440, 1920],
                value=1440,
                help="Browser viewport width used for the screenshot capture.",
            )
            viewport_height = a2.select_slider(
                "Viewport height",
                options=[800, 1000, 1200, 1600],
                value=1200,
                help="Browser viewport height used before full-page capture.",
            )
            full_page = a3.checkbox(
                "Capture full page",
                value=False,
                help="Full-page screenshots are taller and slower, but reveal lower-page attention regions.",
            )

            b1, b2, b3, b4 = st.columns(4)
            map_width_percent = b1.select_slider(
                "Map width",
                options=[60, 70, 80, 90, 100],
                value=90,
                help="Width of the attention map relative to the parent container.",
            )
            map_visible_height = b2.select_slider(
                "Visible height",
                options=[600, 750, 900, 1100, 1300, 1600],
                value=900,
                help="Maximum visible map height. Tall screenshots scroll inside the map.",
            )
            max_regions = b3.select_slider(
                "Max regions",
                options=[25, 50, 80, 120, 160],
                value=80,
                help="Limits overlays so the map remains readable.",
            )
            min_score = b4.select_slider(
                "Minimum score",
                options=[1, 25, 45, 60, 75],
                value=1,
                help="Filter out low-attention overlays.",
            )

            show_score_badges = st.checkbox(
                "Show score badges on overlays",
                value=True,
            )

            force_fresh = st.checkbox(
                "Force fresh capture",
                value=False,
                help="Clears the short cache before running. Useful when testing layout changes.",
            )

    if not run_btn:
        st.info("Enter a URL and generate a free simulated attention map.")
        return

    if not target_url.strip():
        st.warning("Please enter a valid URL.")
        return

    if force_fresh:
        cached_attention_capture.clear()

    with st.status("Capturing page screenshot and extracting visual regions...", expanded=True) as status:
        try:
            data = cached_attention_capture(
                target_url.strip(),
                viewport_width=viewport_width,
                viewport_height=viewport_height,
                full_page=full_page,
            )
            data = _limit_elements(data, max_regions=max_regions, min_score=min_score)
            status.update(label="Attention map generated.", state="complete", expanded=False)
        except Exception as exc:
            status.update(label="Attention map failed.", state="error", expanded=True)
            st.error(f"Could not generate attention map: {type(exc).__name__}: {exc}")
            return

    elements = data.get("elements", [])
    high = sum(1 for e in elements if e.get("attention_level") == "High")
    medium = sum(1 for e in elements if e.get("attention_level") == "Medium")
    low = sum(1 for e in elements if e.get("attention_level") == "Low")

    try:
        image_width, image_height = _image_size_from_b64(data["screenshot_b64"])
    except Exception:
        image_width, image_height = 0, 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Detected regions", len(elements))
    m2.metric("High attention", high)
    m3.metric("Medium attention", medium)
    m4.metric("Low attention", low)
    m5.metric("Screenshot", f"{image_width}×{image_height}" if image_width else "Unknown")

    st.subheader("Interactive Attention Overlay")
    render_attention_map_html(
        data,
        width_percent=map_width_percent,
        max_visible_height=map_visible_height,
        show_score_badges=show_score_badges,
    )

    if data.get("screenshot_b64"):
        st.download_button(
            "Download raw screenshot",
            data=base64.b64decode(data["screenshot_b64"]),
            file_name="attention_map_screenshot.png",
            mime="image/png",
            icon=":material/download:",
        )

    st.subheader("Top Attention Regions")
    rows = []
    for e in elements[:20]:
        rows.append(
            {
                "Score": _safe_int(e.get("attention_score"), 0),
                "Level": e.get("attention_level", "Unknown"),
                "Element": e.get("tag", ""),
                "Text": (e.get("text") or e.get("aria_label") or e.get("href") or "")[:140],
                "X": round(_safe_float(e.get("x"), 0), 1),
                "Y": round(_safe_float(e.get("y"), 0), 1),
                "Width": round(_safe_float(e.get("width"), 0), 1),
                "Height": round(_safe_float(e.get("height"), 0), 1),
            }
        )

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("No attention regions matched the current filters.")

    st.info(
        "This is a simulated attention model based on page structure, not real visitor tracking. "
        "For real click or scroll heatmaps, the target site would need an installed tracking script."
    )
