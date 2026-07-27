"""
pipeline.py — SEO Audit scraping and LLM analysis engine.

This version fixes the previous failure mode where the LLM returned a small
scraped-data summary, Pydantic silently filled the missing report fields with
defaults, and the final audit looked empty.

Design:
1. scrape_seo_targets() collects deterministic SEO signals.
2. _build_deterministic_report() creates a complete non-empty SEOAuditReport.
3. run_local_seo_audit() asks the LLM to improve the report, but never trusts
   incomplete JSON blindly.
4. If the LLM returns partial JSON, invalid JSON, or scraped-data JSON, the
   deterministic report is still returned instead of a blank/default object.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
import urllib.robotparser

from bs4 import BeautifulSoup
import dotenv
import httpx
from pydantic import BaseModel, Field
from supabase import create_client
import streamlit as st

try:
    import textstat
except Exception:  # pragma: no cover
    textstat = None

try:
    import yake
except Exception:  # pragma: no cover
    yake = None

try:
    import spacy
except Exception:  # pragma: no cover
    spacy = None

try:
    from langdetect import DetectorFactory, detect as detect_language_external
    DetectorFactory.seed = 0
except Exception:  # pragma: no cover
    detect_language_external = None

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None


@st.cache_resource
def get_supabase():
    dotenv.load_dotenv()
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Centralised configuration constants
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b"
DEFAULT_OLLAMA_TIMEOUT = 360
DEFAULT_OLLAMA_PING_TIMEOUT = 16.0
DEFAULT_SCRAPE_TIMEOUT = 60
DEFAULT_BODY_SNIPPET_CHARS = 3000
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 4096
DEFAULT_NUM_CTX = 8192
DEFAULT_JS_AUDIT_TIMEOUT = 18.0
DEFAULT_ENABLE_JS_AUDIT_FOR_EXHAUSTIVE = True
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "you", "your", "our",
    "has", "have", "had", "not", "but", "about", "into", "more", "most", "can", "will", "its", "it's",
    "they", "their", "them", "his", "her", "she", "him", "who", "what", "when", "where", "why", "how",
    "all", "any", "one", "two", "new", "use", "using", "used", "get", "make", "made", "page", "site",
    "website", "home", "learn", "read", "click", "here", "there", "over", "under", "then", "than",
}


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
def _default_audit_options() -> dict:
    return {
        "focus_keyword": "",
        "secondary_keywords": "",
        "site_archetype": "General Corporate / Informational",
        "audit_rigor": "Standard Optimization Audit",
        "scrape_timeout": DEFAULT_SCRAPE_TIMEOUT,
        "model_timeout": DEFAULT_OLLAMA_TIMEOUT,
        "temperature": DEFAULT_TEMPERATURE,
        "top_p": DEFAULT_TOP_P,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "seed": None,
        "num_ctx": DEFAULT_NUM_CTX,
        "body_snippet_chars": DEFAULT_BODY_SNIPPET_CHARS,
        "output_language": "English",
        "analysis_depth": "Standard",
        "report_tone": "Technical",
        "repair_incomplete_json": False,
        "enable_js_audit": False,
        "enable_js_audit_for_exhaustive": DEFAULT_ENABLE_JS_AUDIT_FOR_EXHAUSTIVE,
        "js_audit_timeout": DEFAULT_JS_AUDIT_TIMEOUT,
    }


def _resolve_audit_options(options: dict | None) -> dict:
    resolved = _default_audit_options()
    if options:
        resolved.update({k: v for k, v in options.items() if v is not None})
    return resolved


# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------
class SEOAuditReport(BaseModel):
    overall_score: int = Field(default=0)
    category_scores: dict[str, int] = Field(default_factory=lambda: {"Technical": 0, "Content": 0, "UX": 0})

    title_issue: str = Field(default="No significant issues detected.")
    suggested_title: str = Field(default="")
    meta_issue: str = Field(default="No meta description issues analyzed.")
    suggested_meta: str = Field(default="")

    image_alt_analysis: str = Field(default="No image analysis provided.")
    image_alt_quality: int = Field(default=0)
    image_size_optimization: int = Field(default=0)

    link_strategy_analysis: str = Field(default="No link analysis provided.")
    media_and_links_detailed_analysis: str = Field(default="No media and link analysis provided.")
    anchor_text_quality: int = Field(default=0)
    internal_link_relevance_score: int = Field(default=0)

    heading_counts: dict[str, int] = Field(default_factory=lambda: {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0})
    heading_hierarchy_analysis: str = Field(default="No heading structure analysis provided.")
    content_depth_analysis: str = Field(default="No content depth analysis provided.")
    social_tags_analysis: str = Field(default="No social media meta tag analysis provided.")
    indexing_directives_analysis: str = Field(default="No indexing or canonical analysis provided.")
    schema_structured_data_analysis: str = Field(default="No structured data analysis provided.")
    security_performance_analysis: str = Field(default="No security or speed metrics analysis provided.")
    url_structure_analysis: str = Field(default="No URL structural analysis provided.")

    eeat_authority_analysis: str = Field(default="No E-E-A-T indicator analysis provided.")
    readability_user_experience_analysis: str = Field(default="No textual readability analysis provided.")
    faq_breadcrumbs_analysis: str = Field(default="No structural elements analysis provided.")
    content_quality_analysis: str = Field(default="No content quality analysis provided.")
    content_uniqueness_score: int = Field(default=0)
    search_intent_match: int = Field(default=0)
    topic_coverage_score: int = Field(default=0)
    readability_score: int = Field(default=0)

    structured_data_discoverability_score: int = Field(default=0)
    trust_signals_conversion_score: int = Field(default=0)
    trust_meta_structural_analysis: str = Field(default="No meta/trust structural analysis provided.")

    # Discovery Tracking Fields
    title_length_chars: int = Field(default=0)
    title_keyword_position: str = Field(default="")
    meta_length_chars: int = Field(default=0)
    snippet_ctr_potential: int = Field(default=0)
    title_uniqueness: str = Field(default="")
    meta_uniqueness: str = Field(default="")
    open_graph_title: str = Field(default="")
    open_graph_description: str = Field(default="")
    open_graph_image: str = Field(default="")
    twitter_card_image: str = Field(default="")
    favicon_present: bool = Field(default=False)
    site_name_present: bool = Field(default=False)

    # Accessibility & Advanced Semantic Structure Validation Fields
    aria_labels_present: bool = Field(default=False)
    aria_landmarks_present: bool = Field(default=False)
    button_semantics_valid: str = Field(default="Valid")
    list_semantics_valid: str = Field(default="Valid")
    table_semantics_valid: str = Field(default="Valid")
    form_labels_present: bool = Field(default=False)
    alt_quality_score: int = Field(default=0)
    heading_semantics_valid: str = Field(default="Valid")
    landmark_structure_quality: int = Field(default=0)
    contrast_risk_flag: str = Field(default="Low")

    # Link Architecture & Structural Risk Phase Fields
    anchor_text_unique_count: int = Field(default=0)
    exact_match_anchor_overuse: str = Field(default="Low Risk")
    internal_link_context_quality: int = Field(default=0)
    orphan_page_risk: str = Field(default="Low Risk")
    hub_page_links: int = Field(default=0)
    money_page_links: int = Field(default=0)
    deep_page_discoverability: int = Field(default=0)
    navigation_density: float = Field(default=0.0)
    footer_link_bloat: str = Field(default="Normal")
    broken_external_links: int = Field(default=0)

    # Phase 4 Semantic Content Analysis Fields
    primary_topic: str = Field(default="")
    secondary_topics: list[str] = Field(default_factory=list)
    search_intent_type: str = Field(default="")
    entity_coverage: list[str] = Field(default_factory=list)
    topical_completeness: int = Field(default=0)
    content_freshness: str = Field(default="")
    publication_date: str = Field(default="Unknown")
    last_modified_date: str = Field(default="Unknown")
    author_present: bool = Field(default=False)
    author_credentials_present: bool = Field(default=False)
    references_present: bool = Field(default=False)
    source_quality_score: int = Field(default=0)
    duplicate_content_risk: str = Field(default="Low")
    thin_content_flag: bool = Field(default=False)
    keyword_stuffing_risk: str = Field(default="Low")
    content_originality_score: int = Field(default=0)
    readability_grade_level: str = Field(default="")
    language_detected: str = Field(default="")

    # Premium JavaScript Rendering Enrichment Fields
    javascript_rendering_analysis: str = Field(default="No JavaScript rendering analysis performed.")
    js_audit_checked: bool = Field(default=False)
    js_audit_available: bool = Field(default=False)
    js_rendering_risk: str = Field(default="Not checked")
    js_content_dependency: str = Field(default="Not checked")
    rendering_gap_score: int = Field(default=0)
    rendered_word_count: int = Field(default=0)
    rendered_word_delta: int = Field(default=0)
    after_scroll_word_count: int = Field(default=0)
    scroll_revealed_word_delta: int = Field(default=0)
    rendered_h1_count: int = Field(default=0)
    rendered_total_links: int = Field(default=0)
    js_added_links: int = Field(default=0)
    rendered_schema_count: int = Field(default=0)
    schema_added_by_js: bool = Field(default=False)
    above_fold_word_count: int = Field(default=0)
    above_fold_h1_visible: bool = Field(default=False)
    above_fold_primary_cta_visible: bool = Field(default=False)
    title_changed_after_render: bool = Field(default=False)
    meta_changed_after_render: bool = Field(default=False)
    canonical_changed_after_render: bool = Field(default=False)
    robots_changed_after_render: bool = Field(default=False)
    client_side_redirect_detected: bool = Field(default=False)
    js_console_error_count: int = Field(default=0)
    failed_request_count: int = Field(default=0)

    action_item_markdown: str = Field(default="")


REPORT_KEYS = list(SEOAuditReport.model_fields.keys())
NARRATIVE_FIELDS = {
    "title_issue", "suggested_title", "meta_issue", "suggested_meta", "image_alt_analysis",
    "link_strategy_analysis", "media_and_links_detailed_analysis", "heading_hierarchy_analysis",
    "content_depth_analysis", "social_tags_analysis", "indexing_directives_analysis",
    "schema_structured_data_analysis", "security_performance_analysis", "url_structure_analysis",
    "eeat_authority_analysis", "readability_user_experience_analysis", "faq_breadcrumbs_analysis",
    "content_quality_analysis", "trust_meta_structural_analysis", "javascript_rendering_analysis",
    "action_item_markdown",
}
DETERMINISTIC_FIELDS = set(REPORT_KEYS) - NARRATIVE_FIELDS


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------
def _clamp_score(value: float | int, low: int = 0, high: int = 100) -> int:
    try:
        return max(low, min(high, int(round(float(value)))))
    except Exception:
        return low


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _norm_text(value: str) -> str:
    return " ".join((value or "").split())


def _bool_label(value: bool) -> str:
    return "present" if value else "missing"


def _parse_date(value: str | None) -> datetime | None:
    if not value or not str(value).strip() or str(value).strip().lower() == "unknown":
        return None
    raw = str(value).strip()
    for candidate in (raw, raw.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except Exception:
            pass
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        return None


def _date_to_iso(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.date().isoformat()


def _extract_json_object(raw: str) -> str:
    """Return the first JSON object contained in raw text."""
    text = (raw or "").strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


@st.cache_resource
def _get_yake_extractor():
    if yake is None:
        return None
    try:
        return yake.KeywordExtractor(lan="en", n=3, top=10)
    except Exception:
        return None


@st.cache_resource
def _get_spacy_nlp():
    if spacy is None:
        return None
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        logger.warning("spaCy model 'en_core_web_sm' is not installed. Entity extraction will use keyword fallback.")
        return None


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9']+", (text or "").lower())


def _meaningful_words(text: str) -> list[str]:
    return [w for w in _words(text) if len(w) > 2 and w not in STOPWORDS]


def _detect_language(text: str, html_lang: str = "") -> str:
    html_lang = _safe_text(html_lang).lower()
    if html_lang and html_lang != "missing":
        return html_lang.split("-")[0].split("_")[0]
    if detect_language_external and len(_norm_text(text)) >= 80:
        try:
            return detect_language_external(text[:5000]).lower()
        except Exception:
            pass
    return "unknown"


def _extract_topics(text: str, title: str = "", meta: str = "") -> tuple[str, list[str]]:
    source = _norm_text(" ".join([title or "", meta or "", text or ""]))
    extractor = _get_yake_extractor()
    keywords: list[str] = []
    if extractor and source:
        try:
            pairs = sorted(extractor.extract_keywords(source), key=lambda item: item[1])
            for phrase, _score in pairs:
                phrase = _norm_text(phrase)
                if phrase and phrase.lower() not in [k.lower() for k in keywords]:
                    keywords.append(phrase)
        except Exception:
            keywords = []

    if not keywords:
        fallback = title if title and title != "Missing" else meta
        chunks = [c.strip() for c in re.split(r"[|:;\-–—]", fallback or "") if c.strip()]
        if chunks:
            keywords = chunks[:6]

    primary = keywords[0] if keywords else "Unclear primary topic"
    secondary = keywords[1:6] if len(keywords) > 1 else []
    return primary[:140], secondary


def _extract_entities(text: str, language: str, fallback_topics: list[str]) -> list[str]:
    if language.startswith("en"):
        nlp = _get_spacy_nlp()
        if nlp is not None:
            try:
                doc = nlp(text[:8000])
                entities: list[str] = []
                for ent in doc.ents:
                    entity = _norm_text(ent.text)
                    if entity and entity not in entities:
                        entities.append(entity)
                if entities:
                    return entities[:20]
            except Exception:
                pass
    return fallback_topics[:20]


def _infer_search_intent(title: str, meta: str, body: str, focus_keyword: str = "") -> str:
    text = " ".join([title, meta, body[:3000], focus_keyword]).lower()
    transactional = ["buy", "checkout", "order", "purchase", "subscribe", "register", "sign up", "get started", "pricing", "quote", "book a demo"]
    commercial = ["best", "review", "compare", "comparison", "vs", "alternatives", "top", "pricing", "plans"]
    navigational = ["login", "sign in", "dashboard", "account", "contact", "support", "docs", "documentation"]
    informational = ["what is", "how to", "guide", "tutorial", "learn", "why", "examples", "resources", "blog"]
    if any(t in text for t in transactional):
        return "Transactional"
    if any(t in text for t in commercial):
        return "Commercial"
    if any(t in text for t in navigational):
        return "Navigational"
    if any(t in text for t in informational):
        return "Informational"
    return "Informational"


def _keyword_position(title: str, focus_keyword: str, primary_topic: str) -> str:
    title_lower = (title or "").lower()
    keyword = (focus_keyword or primary_topic or "").lower().strip()
    if not title_lower or not keyword or title == "Missing":
        return "Missing"
    idx = title_lower.find(keyword)
    if idx < 0:
        # fallback: check first token of primary topic
        tokens = _meaningful_words(keyword)
        if tokens:
            idx = title_lower.find(tokens[0])
    if idx < 0:
        return "Missing"
    ratio = idx / max(1, len(title_lower))
    if ratio <= 0.25:
        return "Front-loaded"
    if ratio <= 0.65:
        return "Middle"
    return "End"


def _uniqueness_label(text: str) -> str:
    tokens = _meaningful_words(text)
    if not tokens:
        return "Low"
    ratio = len(set(tokens)) / len(tokens)
    if ratio >= 0.85 and len(tokens) >= 5:
        return "High"
    if ratio >= 0.65:
        return "Medium"
    return "Low"


def _snippet_ctr_score(title_len: int, meta_len: int, has_og: bool, favicon: bool, title_unique: str, meta_unique: str) -> int:
    score = 35
    if 50 <= title_len <= 60:
        score += 20
    elif 30 <= title_len <= 70:
        score += 10
    else:
        score -= 10
    if 120 <= meta_len <= 160:
        score += 20
    elif 80 <= meta_len <= 180:
        score += 10
    else:
        score -= 10
    score += 10 if has_og else 0
    score += 5 if favicon else 0
    score += 5 if title_unique == "High" else 0
    score += 5 if meta_unique == "High" else 0
    return _clamp_score(score)


def _content_freshness(publication_date: str, last_modified_date: str) -> str:
    dt_obj = _parse_date(last_modified_date) or _parse_date(publication_date)
    if not dt_obj:
        return "Unknown"
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    age = max(0, (datetime.now(timezone.utc) - dt_obj.astimezone(timezone.utc)).days)
    if age <= 30:
        return f"Fresh ({age} days old)"
    if age <= 90:
        return f"Recent ({age} days old)"
    if age <= 365:
        return f"Moderate ({age} days old)"
    return f"Stale ({age} days old)"


def _readability_grade(text: str, language: str) -> str:
    if not text or not language.startswith("en") or textstat is None:
        return "Unknown"
    try:
        grade = textstat.flesch_kincaid_grade(text)
        return f"Grade {grade:.1f}"
    except Exception:
        return "Unknown"


def _keyword_stuffing_risk(text: str) -> str:
    words = _meaningful_words(text)
    if not words:
        return "Low"
    word, count = Counter(words).most_common(1)[0]
    density = count / max(1, len(words)) * 100
    if density > 8:
        return "High"
    if density > 5:
        return "Medium"
    return "Low"


def _duplicate_content_risk(text: str) -> str:
    sentences = [s.strip().lower() for s in re.split(r"[.!?]+\s*", text or "") if len(s.strip()) > 20]
    words = _meaningful_words(text)
    if not words:
        return "Low"
    lexical_ratio = len(set(words)) / max(1, len(words))
    sentence_ratio = len(set(sentences)) / max(1, len(sentences)) if sentences else 1
    if lexical_ratio < 0.35 or sentence_ratio < 0.5:
        return "High"
    if lexical_ratio < 0.5 or sentence_ratio < 0.75:
        return "Medium"
    return "Low"


def _originality_score(text: str) -> int:
    words = _meaningful_words(text)
    if not words:
        return 0
    lexical_ratio = len(set(words)) / max(1, len(words))
    score = lexical_ratio * 100
    if _duplicate_content_risk(text) == "Medium":
        score -= 10
    elif _duplicate_content_risk(text) == "High":
        score -= 25
    return _clamp_score(score)


def _source_quality_score(scraped: dict) -> int:
    score = 0
    score += 10 if scraped.get("is_https") else 0
    score += 10 if scraped.get("author_present") else 0
    score += 10 if scraped.get("author_credentials_present") else 0
    score += 10 if scraped.get("references_present") else 0
    score += 8 if scraped.get("has_about_page") else 0
    score += 8 if scraped.get("has_contact_page") else 0
    score += 8 if scraped.get("has_privacy_policy") else 0
    score += 8 if int(scraped.get("schema_count", 0) or 0) > 0 else 0
    score += 5 if scraped.get("favicon_present") else 0
    score += 5 if scraped.get("site_name_present") else 0
    score += 5 if scraped.get("open_graph_present") else 0
    score += 5 if scraped.get("twitter_cards_present") else 0
    score += 8 if scraped.get("publication_date") != "Unknown" or scraped.get("last_modified_date") != "Unknown" else 0
    return _clamp_score(score)


def _topical_completeness(scraped: dict) -> int:
    word_count = int(scraped.get("word_count", 0) or 0)
    heading_counts = scraped.get("heading_counts", {}) if isinstance(scraped.get("heading_counts"), dict) else {}
    entities = scraped.get("entity_coverage", []) if isinstance(scraped.get("entity_coverage"), list) else []
    score = 0
    score += min(35, word_count // 40)
    score += min(20, sum(1 for i in range(1, 7) if int(heading_counts.get(f"h{i}", 0) or 0) > 0) * 4)
    score += min(20, len(entities) * 2)
    score += 8 if scraped.get("references_present") else 0
    score += 8 if scraped.get("author_present") else 0
    score += 5 if scraped.get("publication_date") != "Unknown" or scraped.get("last_modified_date") != "Unknown" else 0
    return _clamp_score(score)


def _button_semantics_label(invalid_count: int, total_links: int) -> str:
    if invalid_count <= 0:
        return "Valid"
    ratio = invalid_count / max(1, total_links)
    return "Invalid" if ratio > 0.2 else "Sub-optimized"


def _heading_semantics_label(heading_counts: dict, h1_count: int) -> str:
    if h1_count == 0:
        return "Missing H1"
    if h1_count > 1:
        return "Duplicate H1"
    if int(heading_counts.get("h2", 0) or 0) == 0 and any(int(heading_counts.get(f"h{i}", 0) or 0) > 0 for i in [3, 4, 5, 6]):
        return "Level Skipping Detected"
    return "Valid"


def _extract_dates(soup: BeautifulSoup, headers: httpx.Headers) -> tuple[str, str]:
    pub_selectors = [
        soup.find("meta", property="article:published_time"),
        soup.find("meta", property="og:article:published_time"),
        soup.find("meta", attrs={"name": "pubdate"}),
        soup.find("meta", attrs={"name": "date"}),
        soup.find("meta", attrs={"itemprop": "datePublished"}),
        soup.find("time", attrs={"datetime": True}),
    ]
    mod_selectors = [
        soup.find("meta", property="article:modified_time"),
        soup.find("meta", attrs={"name": "last-modified"}),
        soup.find("meta", attrs={"itemprop": "dateModified"}),
    ]

    publication = "Unknown"
    modified = "Unknown"
    for tag in pub_selectors:
        if not tag:
            continue
        raw = tag.get("content", "") or tag.get("datetime", "") or tag.get_text(" ", strip=True)
        date = _parse_date(raw)
        if date:
            publication = _date_to_iso(date)
            break
    for tag in mod_selectors:
        if not tag:
            continue
        raw = tag.get("content", "") or tag.get("datetime", "") or tag.get_text(" ", strip=True)
        date = _parse_date(raw)
        if date:
            modified = _date_to_iso(date)
            break
    header_last_modified = headers.get("Last-Modified")
    if header_last_modified:
        header_date = _parse_date(header_last_modified)
        if header_date:
            modified = _date_to_iso(header_date)
    return publication, modified


def _clean_body_text(html_text: str, snippet_limit: int) -> str:
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(NOISE_TAGS):
        tag.decompose()
    content = " ".join(
        node.get_text(" ", strip=True)
        for node in soup.find_all(["main", "article", "section", "p", "li", "h1", "h2", "h3"])
    )
    content = _norm_text(content)
    if len(content) < 250:
        content = _norm_text(soup.get_text(" ", strip=True))
    return content[:snippet_limit]


def _semantic_enrichment(scraped: dict, focus_keyword: str = "") -> dict:
    title = scraped.get("title", "")
    meta = scraped.get("meta_description", "")
    body = scraped.get("body_context_snippet", "")

    language = _detect_language(body or title or meta, scraped.get("html_lang", ""))
    primary, secondary = _extract_topics(body, title, meta)
    entities = _extract_entities(body, language, [primary, *secondary])
    publication = scraped.get("publication_date") or scraped.get("scraped_publication_date") or "Unknown"
    modified = scraped.get("last_modified_date") or scraped.get("scraped_last_modified_date") or "Unknown"

    enriched = dict(scraped)
    enriched.update({
        "language_detected": language,
        "primary_topic": primary,
        "secondary_topics": secondary,
        "entity_coverage": entities,
        "search_intent_type": _infer_search_intent(title, meta, body, focus_keyword),
        "publication_date": publication or "Unknown",
        "last_modified_date": modified or "Unknown",
        "content_freshness": _content_freshness(publication, modified),
        "readability_grade_level": _readability_grade(body, language),
        "keyword_stuffing_risk": _keyword_stuffing_risk(body),
        "duplicate_content_risk": _duplicate_content_risk(body),
        "content_originality_score": _originality_score(body),
        "thin_content_flag": int(scraped.get("word_count", 0) or 0) < 300,
    })
    enriched["source_quality_score"] = _source_quality_score(enriched)
    enriched["topical_completeness"] = _topical_completeness(enriched)
    return enriched



# ---------------------------------------------------------------------------
# Premium JavaScript rendering enrichment
# ---------------------------------------------------------------------------
def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalized_compare_text(value: Any) -> str:
    text = _safe_text(value).strip()
    if text.lower() in {"missing", "none detected", "unknown", "null", "none"}:
        return ""
    return text.rstrip("/").lower()


def _metadata_changed_after_render(raw_value: Any, rendered_value: Any) -> bool:
    return _normalized_compare_text(raw_value) != _normalized_compare_text(rendered_value)


def _schema_types_from_jsonld_blocks(blocks: list[str]) -> list[str]:
    types: list[str] = []

    def add_type(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                add_type(item)
            return
        if value is not None:
            label = _safe_text(value)
            if label and label not in types:
                types.append(label)

    def walk(item: Any) -> None:
        if isinstance(item, list):
            for child in item:
                walk(child)
        elif isinstance(item, dict):
            if "@type" in item:
                add_type(item.get("@type"))
            if isinstance(item.get("@graph"), list):
                walk(item["@graph"])

    for raw in blocks or []:
        try:
            parsed = json.loads(raw)
            walk(parsed)
        except Exception:
            continue

    return types[:30] if types else ["None Detected"]


def _should_run_js_audit(options: dict | None) -> bool:
    opts = _resolve_audit_options(options)
    explicit = bool(opts.get("enable_js_audit", False))
    premium_by_depth = (
        bool(opts.get("enable_js_audit_for_exhaustive", True))
        and _safe_text(opts.get("analysis_depth", "")).lower() == "exhaustive"
    )
    premium_by_name = _safe_text(opts.get("analysis_mode", "")).lower() in {
        "premium",
        "exhaustive ai summary",
        "exhaustive",
    }
    return explicit or premium_by_depth or premium_by_name


def _js_rendering_risk_label(scraped: dict) -> str:
    if not scraped.get("js_audit_checked"):
        return "Not checked"

    if not scraped.get("js_audit_available"):
        return "Unavailable"

    dependency = _safe_text(scraped.get("js_content_dependency", "Low"))
    changed_meta = any([
        scraped.get("title_changed_after_render"),
        scraped.get("meta_changed_after_render"),
        scraped.get("canonical_changed_after_render"),
        scraped.get("robots_changed_after_render"),
    ])
    js_added_links = _safe_int(scraped.get("js_added_links", 0))
    console_errors = _safe_int(scraped.get("js_console_error_count", 0))
    failed_requests = _safe_int(scraped.get("failed_request_count", 0))

    if dependency == "High" or changed_meta:
        return "High"

    if dependency == "Medium" or js_added_links > 20 or console_errors >= 5 or failed_requests >= 8:
        return "Medium"

    return "Low"


def _javascript_rendering_summary(scraped: dict) -> str:
    if not scraped.get("js_audit_checked"):
        return "JavaScript rendering audit was not run for this mode."

    if not scraped.get("js_audit_available"):
        error = _safe_text(scraped.get("js_audit_error", "No browser-rendered data was collected."))
        return f"JavaScript rendering audit was attempted but unavailable. Reason: {error}"

    raw_words = _safe_int(scraped.get("word_count", 0))
    rendered_words = _safe_int(scraped.get("rendered_word_count", 0))
    word_delta = _safe_int(scraped.get("rendered_word_delta", 0))
    js_links = _safe_int(scraped.get("js_added_links", 0))
    risk = _js_rendering_risk_label(scraped)
    dependency = _safe_text(scraped.get("js_content_dependency", "Low"))

    metadata_flags = []
    if scraped.get("title_changed_after_render"):
        metadata_flags.append("title")
    if scraped.get("meta_changed_after_render"):
        metadata_flags.append("meta description")
    if scraped.get("canonical_changed_after_render"):
        metadata_flags.append("canonical")
    if scraped.get("robots_changed_after_render"):
        metadata_flags.append("robots")

    metadata_note = (
        f" Rendered metadata changed after JavaScript execution for: {', '.join(metadata_flags)}."
        if metadata_flags
        else " Rendered metadata stayed consistent with the raw HTML for title, meta description, canonical, and robots directives."
    )

    return (
        f"JavaScript SEO risk is {risk}. The raw HTML contains {raw_words} word(s), while the rendered DOM contains "
        f"{rendered_words} word(s), creating a rendered-content delta of {word_delta}. JavaScript content dependency is "
        f"{dependency}, with {js_links} link(s) added after rendering, {scraped.get('rendered_schema_count', 0)} rendered schema "
        f"block(s), and {scraped.get('js_console_error_count', 0)} browser console error(s)."
        f"{metadata_note} Above-the-fold checks found H1 visibility={scraped.get('above_fold_h1_visible', False)} "
        f"and primary CTA visibility={scraped.get('above_fold_primary_cta_visible', False)}."
    )


def scrape_js_specific_signals(
    url: str,
    raw_scraped: dict,
    timeout: float = DEFAULT_JS_AUDIT_TIMEOUT,
) -> dict:
    """
    Browser-rendering enrichment layer for premium audits.

    This function intentionally does not replace scrape_seo_targets(). It only
    collects SEO signals that require JavaScript execution, browser rendering,
    viewport visibility, resource loading, and post-render DOM inspection.
    """

    if sync_playwright is None:
        return {
            "js_audit_checked": True,
            "js_audit_available": False,
            "js_audit_error": "Playwright is not installed. Install it with `pip install playwright` and run `playwright install chromium`.",
        }

    console_errors: list[str] = []
    console_warnings: list[str] = []
    failed_requests: list[str] = []

    raw_word_count = _safe_int(raw_scraped.get("word_count", 0))
    raw_total_links = _safe_int(raw_scraped.get("total_links", 0))
    raw_schema_count = _safe_int(raw_scraped.get("schema_count", 0))
    raw_final_url = _safe_text(raw_scraped.get("final_url", url)) or url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1365, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            def handle_console(msg) -> None:
                try:
                    if msg.type == "error":
                        console_errors.append(_safe_text(msg.text)[:300])
                    elif msg.type == "warning":
                        console_warnings.append(_safe_text(msg.text)[:300])
                except Exception:
                    pass

            def handle_request_failed(req) -> None:
                try:
                    failed_requests.append(_safe_text(req.url)[:300])
                except Exception:
                    pass

            page.on("console", handle_console)
            page.on("requestfailed", handle_request_failed)

            page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))

            try:
                page.wait_for_load_state("networkidle", timeout=3500)
            except Exception:
                pass

            page.wait_for_timeout(900)

            initial_data = page.evaluate(
                """
                () => {
                    const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();

                    const getMeta = (selector) => {
                        const el = document.querySelector(selector);
                        return el ? clean(el.getAttribute("content")) : "";
                    };

                    const getLink = (selector) => {
                        const el = document.querySelector(selector);
                        return el ? clean(el.getAttribute("href")) : "";
                    };

                    const visible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();

                        return (
                            style.display !== "none" &&
                            style.visibility !== "hidden" &&
                            Number(style.opacity || 1) > 0 &&
                            rect.width > 0 &&
                            rect.height > 0
                        );
                    };

                    const text = clean(document.body ? document.body.innerText : "");

                    const headings = {};
                    ["h1", "h2", "h3", "h4", "h5", "h6"].forEach((tag) => {
                        headings[tag] = Array.from(document.querySelectorAll(tag))
                            .map((el) => clean(el.innerText))
                            .filter(Boolean);
                    });

                    const links = Array.from(document.querySelectorAll("a[href]"))
                        .map((a) => ({
                            href: a.href,
                            text: clean(a.innerText || a.getAttribute("aria-label") || "")
                        }))
                        .filter((item) => item.href);

                    const schemaBlocks = Array.from(
                        document.querySelectorAll('script[type="application/ld+json"]')
                    ).map((el) => el.textContent || "");

                    const ctaPattern = /(start|sign up|get started|buy|book|demo|contact|subscribe|audit|try|checkout|register|pricing)/i;

                    const aboveFoldCandidates = Array.from(
                        document.querySelectorAll("h1, h2, p, a, button")
                    ).filter((el) => {
                        const rect = el.getBoundingClientRect();
                        return visible(el) && rect.top >= 0 && rect.top <= window.innerHeight;
                    });

                    const aboveFoldText = clean(
                        aboveFoldCandidates.map((el) => el.innerText || "").join(" ")
                    );

                    const aboveFoldCtas = aboveFoldCandidates
                        .map((el) => clean(el.innerText || el.getAttribute("aria-label") || ""))
                        .filter((txt) => ctaPattern.test(txt))
                        .slice(0, 8);

                    const buttonNavigationCount = Array.from(document.querySelectorAll("button"))
                        .filter((btn) => {
                            const text = clean(btn.innerText || btn.getAttribute("aria-label") || "");
                            const onclick = btn.getAttribute("onclick") || "";
                            return ctaPattern.test(text) && /(location|href|router|navigate)/i.test(onclick);
                        }).length;

                    const resources = performance.getEntriesByType("resource").map((r) => ({
                        name: r.name,
                        type: r.initiatorType,
                        transferSize: r.transferSize || 0
                    }));

                    const host = window.location.hostname;
                    const thirdPartyResourceCount = resources.filter((r) => {
                        try {
                            return new URL(r.name).hostname !== host;
                        } catch {
                            return false;
                        }
                    }).length;

                    return {
                        browser_final_url: window.location.href,
                        rendered_title: clean(document.title),
                        rendered_meta_description: getMeta('meta[name="description"]'),
                        rendered_meta_robots: getMeta('meta[name="robots"]'),
                        rendered_canonical_url: getLink('link[rel="canonical"]'),
                        rendered_text: text,
                        rendered_word_count: text ? text.split(/\\s+/).filter(Boolean).length : 0,
                        rendered_heading_counts: {
                            h1: headings.h1.length,
                            h2: headings.h2.length,
                            h3: headings.h3.length,
                            h4: headings.h4.length,
                            h5: headings.h5.length,
                            h6: headings.h6.length,
                        },
                        rendered_h1_texts: headings.h1,
                        rendered_total_links: links.length,
                        rendered_links: links.slice(0, 500),
                        rendered_schema_count: schemaBlocks.length,
                        rendered_schema_raw: schemaBlocks.slice(0, 20),
                        above_fold_text: aboveFoldText,
                        above_fold_word_count: aboveFoldText
                            ? aboveFoldText.split(/\\s+/).filter(Boolean).length
                            : 0,
                        above_fold_h1_visible: Array.from(document.querySelectorAll("h1"))
                            .some((h) => {
                                const rect = h.getBoundingClientRect();
                                return visible(h) && rect.top >= 0 && rect.top <= window.innerHeight;
                            }),
                        above_fold_primary_cta_visible: aboveFoldCtas.length > 0,
                        above_fold_cta_texts: aboveFoldCtas,
                        button_navigation_count: buttonNavigationCount,
                        resource_count: resources.length,
                        js_resource_count: resources.filter((r) => r.type === "script").length,
                        css_resource_count: resources.filter((r) => r.type === "link" || r.type === "css").length,
                        image_resource_count: resources.filter((r) => r.type === "img").length,
                        total_transfer_size_kb: Math.round(
                            resources.reduce((sum, r) => sum + (r.transferSize || 0), 0) / 1024
                        ),
                        third_party_resource_count: thirdPartyResourceCount,
                    };
                }
                """
            )

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1100)

            after_scroll_data = page.evaluate(
                """
                () => {
                    const clean = (value) => (value || "").replace(/\\s+/g, " ").trim();
                    const text = clean(document.body ? document.body.innerText : "");
                    return {
                        after_scroll_word_count: text
                            ? text.split(/\\s+/).filter(Boolean).length
                            : 0
                    };
                }
                """
            )

            browser.close()

        rendered_word_count = _safe_int(initial_data.get("rendered_word_count", 0))
        rendered_total_links = _safe_int(initial_data.get("rendered_total_links", 0))
        rendered_schema_count = _safe_int(initial_data.get("rendered_schema_count", 0))
        after_scroll_word_count = _safe_int(after_scroll_data.get("after_scroll_word_count", rendered_word_count))

        rendered_word_delta = rendered_word_count - raw_word_count
        scroll_revealed_word_delta = max(0, after_scroll_word_count - rendered_word_count)

        if raw_word_count <= 0:
            rendering_gap_score = 100 if rendered_word_count > 100 else 0
        else:
            rendering_gap_score = _clamp_score((max(0, rendered_word_delta) / max(1, raw_word_count)) * 100)

        if raw_word_count < 300 and rendered_word_count > 900:
            js_content_dependency = "High"
        elif rendering_gap_score >= 75 or rendered_word_delta >= 700:
            js_content_dependency = "Medium"
        else:
            js_content_dependency = "Low"

        parsed_raw_final = urlparse(raw_final_url)
        base_domain = parsed_raw_final.netloc
        rendered_links = initial_data.get("rendered_links", []) if isinstance(initial_data.get("rendered_links", []), list) else []
        rendered_internal_links = 0
        rendered_external_links = 0
        for link in rendered_links:
            href = _safe_text(link.get("href", "")) if isinstance(link, dict) else ""
            if not href:
                continue
            parsed_href = urlparse(href)
            if parsed_href.netloc in ["", base_domain]:
                rendered_internal_links += 1
            else:
                rendered_external_links += 1

        rendered_schema_types = _schema_types_from_jsonld_blocks(initial_data.get("rendered_schema_raw", []))

        raw_title = raw_scraped.get("title", "")
        raw_meta = raw_scraped.get("meta_description", "")
        raw_canonical = raw_scraped.get("canonical_url", "")
        raw_robots = raw_scraped.get("meta_robots", "")
        browser_final_url = _safe_text(initial_data.get("browser_final_url", ""))

        result = {
            "js_audit_checked": True,
            "js_audit_available": True,
            "browser_initial_url": url,
            "browser_final_url": browser_final_url,
            "client_side_redirect_detected": (
                _normalized_compare_text(browser_final_url)
                != _normalized_compare_text(raw_final_url)
            ),
            "rendered_word_count": rendered_word_count,
            "rendered_word_delta": rendered_word_delta,
            "rendering_gap_score": rendering_gap_score,
            "js_content_dependency": js_content_dependency,
            "rendered_title": initial_data.get("rendered_title", ""),
            "rendered_meta_description": initial_data.get("rendered_meta_description", ""),
            "rendered_canonical_url": initial_data.get("rendered_canonical_url", ""),
            "rendered_meta_robots": initial_data.get("rendered_meta_robots", ""),
            "title_changed_after_render": _metadata_changed_after_render(raw_title, initial_data.get("rendered_title", "")),
            "meta_changed_after_render": _metadata_changed_after_render(raw_meta, initial_data.get("rendered_meta_description", "")),
            "canonical_changed_after_render": _metadata_changed_after_render(raw_canonical, initial_data.get("rendered_canonical_url", "")),
            "robots_changed_after_render": _metadata_changed_after_render(raw_robots, initial_data.get("rendered_meta_robots", "")),
            "rendered_heading_counts": initial_data.get("rendered_heading_counts", {}),
            "rendered_h1_count": _safe_int(initial_data.get("rendered_heading_counts", {}).get("h1", 0) if isinstance(initial_data.get("rendered_heading_counts"), dict) else 0),
            "rendered_h1_texts": initial_data.get("rendered_h1_texts", []),
            "rendered_total_links": rendered_total_links,
            "rendered_internal_links": rendered_internal_links,
            "rendered_external_links": rendered_external_links,
            "js_added_links": max(0, rendered_total_links - raw_total_links),
            "button_navigation_count": _safe_int(initial_data.get("button_navigation_count", 0)),
            "rendered_schema_count": rendered_schema_count,
            "rendered_detected_schema_types": rendered_schema_types,
            "schema_added_by_js": rendered_schema_count > raw_schema_count,
            "above_fold_text": initial_data.get("above_fold_text", "")[:1200],
            "above_fold_word_count": _safe_int(initial_data.get("above_fold_word_count", 0)),
            "above_fold_h1_visible": bool(initial_data.get("above_fold_h1_visible", False)),
            "above_fold_primary_cta_visible": bool(initial_data.get("above_fold_primary_cta_visible", False)),
            "above_fold_cta_texts": initial_data.get("above_fold_cta_texts", []),
            "after_scroll_word_count": after_scroll_word_count,
            "scroll_revealed_word_delta": scroll_revealed_word_delta,
            "resource_count": _safe_int(initial_data.get("resource_count", 0)),
            "js_resource_count": _safe_int(initial_data.get("js_resource_count", 0)),
            "css_resource_count": _safe_int(initial_data.get("css_resource_count", 0)),
            "image_resource_count": _safe_int(initial_data.get("image_resource_count", 0)),
            "total_transfer_size_kb": _safe_int(initial_data.get("total_transfer_size_kb", 0)),
            "third_party_resource_count": _safe_int(initial_data.get("third_party_resource_count", 0)),
            "js_console_error_count": len(console_errors),
            "js_console_warning_count": len(console_warnings),
            "failed_request_count": len(failed_requests),
            "js_console_errors_preview": console_errors[:5],
            "js_console_warnings_preview": console_warnings[:5],
            "failed_requests_preview": failed_requests[:5],
        }
        result["js_rendering_risk"] = _js_rendering_risk_label(result)
        result["javascript_rendering_analysis"] = _javascript_rendering_summary({**raw_scraped, **result})
        return result

    except Exception as exc:
        logger.warning("Playwright JS audit failed for %s: %s", url, exc)
        return {
            "js_audit_checked": True,
            "js_audit_available": False,
            "js_audit_error": f"{type(exc).__name__}: {exc}",
            "js_rendering_risk": "Unavailable",
            "javascript_rendering_analysis": f"JavaScript rendering audit was attempted but failed: {type(exc).__name__}: {exc}",
        }


def _maybe_enrich_with_js_audit(scraped_data: dict, options: dict | None) -> dict:
    data = dict(scraped_data)
    if not _should_run_js_audit(options):
        data.setdefault("js_audit_checked", False)
        data.setdefault("js_audit_available", False)
        data.setdefault("js_rendering_risk", "Not checked")
        return data

    if data.get("js_audit_checked"):
        return data

    audit_url = _safe_text(data.get("final_url") or data.get("url"))
    if not audit_url:
        data.update({
            "js_audit_checked": True,
            "js_audit_available": False,
            "js_audit_error": "No URL was available for JavaScript rendering audit.",
            "js_rendering_risk": "Unavailable",
        })
        data["javascript_rendering_analysis"] = _javascript_rendering_summary(data)
        return data

    timeout = _safe_float(_resolve_audit_options(options).get("js_audit_timeout"), DEFAULT_JS_AUDIT_TIMEOUT)
    js_signals = scrape_js_specific_signals(audit_url, raw_scraped=data, timeout=timeout)
    data.update(js_signals)
    data["js_rendering_risk"] = _js_rendering_risk_label(data)
    data["javascript_rendering_analysis"] = _javascript_rendering_summary(data)
    return data

# ---------------------------------------------------------------------------
# Scraping engine
# ---------------------------------------------------------------------------
def scrape_seo_targets(
    url: str,
    scrape_timeout: float | None = None,
    body_snippet_chars: int | None = None,
    enable_js_audit: bool = False,
    js_audit_timeout: float | None = None,
) -> dict:
    """Crawl *url* and return a dict of SEO-relevant signals."""
    timeout = scrape_timeout if scrape_timeout is not None else DEFAULT_SCRAPE_TIMEOUT
    snippet_limit = body_snippet_chars if body_snippet_chars is not None else DEFAULT_BODY_SNIPPET_CHARS
    resolved_js_audit_timeout = js_audit_timeout if js_audit_timeout is not None else DEFAULT_JS_AUDIT_TIMEOUT

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
            response = client.get(url)
            response_time_sec = response.elapsed.total_seconds()
            page_size_kb = len(response.content) / 1024.0

            status_code = response.status_code
            final_url = str(response.url)
            redirect_chain = [str(r.url) for r in response.history]
            redirect_count = len(response.history)
            content_type = response.headers.get("Content-Type", "Unknown")
            x_robots_tag_header = response.headers.get("X-Robots-Tag")

            parsed_final = urlparse(final_url)
            base_url = f"{parsed_final.scheme}://{parsed_final.netloc}"
            robots_url = urljoin(base_url, "/robots.txt")

            robots_txt_present = False
            robots_txt_blocks_page = False
            sitemap_urls: list[str] = []
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                robots_resp = client.get(robots_url, timeout=timeout)
                if robots_resp.status_code == 200:
                    robots_txt_present = True
                    rp.parse(robots_resp.text.splitlines())
                    robots_txt_blocks_page = not rp.can_fetch("*", final_url)
                    sitemap_urls.extend(rp.site_maps() or [])
            except Exception:
                logger.warning("Failed to fetch or parse robots.txt for %s", base_url)

            if not sitemap_urls:
                try:
                    sitemap_fallback = urljoin(base_url, "/sitemap.xml")
                    sm_resp = client.head(sitemap_fallback, timeout=timeout)
                    if sm_resp.status_code == 200:
                        sitemap_urls.append(sitemap_fallback)
                except Exception:
                    pass
            sitemap_present = bool(sitemap_urls)

            soup = BeautifulSoup(response.text, "html.parser")

            title_tag = soup.title.string.strip() if soup.title and soup.title.string else "Missing"
            meta_tag = soup.find("meta", attrs={"name": "description"})
            meta_desc = meta_tag["content"].strip() if meta_tag and meta_tag.has_attr("content") else "Missing"

            heading_counts = {f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)}
            h1_tags = [h.get_text(" ", strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
            fallback_heading_candidates = 0
            if all(v == 0 for v in heading_counts.values()):
                fallback_heading_candidates = len(soup.select('[role="heading"], .heading, .title, .hero-title, .page-title'))

            images = soup.find_all("img")
            total_images = len(images)
            images_missing_alt = len([img for img in images if not img.get("alt")])
            lazy_loading_used = len([img for img in images if img.get("loading") == "lazy" or "lazy" in img.get("class", [])])
            unoptimized_image_formats = 0
            for img in images:
                src = img.get("src", "").lower()
                if any(src.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                    unoptimized_image_formats += 1

            canonical_elements = soup.find_all("link", rel="canonical")
            multiple_canonicals = len(canonical_elements) > 1
            raw_canonical_href = canonical_elements[0].get("href", "").strip() if canonical_elements else ""
            canonical_url = urljoin(final_url, raw_canonical_href) if raw_canonical_href else "Missing"
            canonical_status_code = 0
            canonical_chain_length = 0
            canonical_points_to_self = False
            canonical_mismatch = False
            if raw_canonical_href:
                parsed_canonical = urlparse(canonical_url)
                canonical_mismatch = parsed_canonical.scheme != parsed_final.scheme or parsed_canonical.netloc != parsed_final.netloc
                try:
                    canonical_resp = client.get(canonical_url, timeout=timeout)
                    canonical_status_code = canonical_resp.status_code
                    canonical_chain_length = len(canonical_resp.history)
                    canonical_points_to_self = str(canonical_resp.url).rstrip("/") == final_url.rstrip("/")
                except Exception:
                    canonical_status_code = 0

            parameterized_duplicate_risk = bool(parsed_final.query) and (not raw_canonical_href or not canonical_points_to_self)

            html_tag = soup.find("html")
            html_lang = html_tag.get("lang", "").strip() if html_tag and html_tag.has_attr("lang") else "Missing"
            source_language = html_lang.split("-")[0].split("_")[0].lower() if html_lang != "Missing" else "Unknown"

            actual_hreflang_tags = [tag for tag in soup.find_all("link", rel="alternate") if tag.has_attr("hreflang")]
            hreflang_present = bool(actual_hreflang_tags)
            hreflang_types: list[str] = []
            hreflang_errors: list[str] = []
            if actual_hreflang_tags:
                has_x_default = False
                for tag in actual_hreflang_tags:
                    lang = tag.get("hreflang", "").strip()
                    href = tag.get("href", "").strip()
                    if lang:
                        hreflang_types.append(lang)
                        if lang.lower() == "x-default":
                            has_x_default = True
                        if " " in lang:
                            hreflang_errors.append(f"Invalid hreflang token with spaces: {lang}")
                    else:
                        hreflang_errors.append("Empty hreflang value detected")
                    if not href:
                        hreflang_errors.append(f"Missing href for hreflang {lang or 'unknown'}")
                    elif not urlparse(href).scheme or not urlparse(href).netloc:
                        hreflang_errors.append(f"Relative hreflang URL detected: {href}")
                if len(set(hreflang_types)) > 1 and not has_x_default:
                    hreflang_errors.append("Multilingual hreflang set is missing x-default")
                hreflang_types = list(dict.fromkeys(hreflang_types))

            publication_date, last_modified_date = _extract_dates(soup, response.headers)
            author_tag = soup.find("meta", attrs={"name": "author"}) or soup.find("a", rel="author") or soup.find("meta", property="article:author")
            author_present = author_tag is not None
            author_text = ""
            if author_tag:
                author_text = author_tag.get("content", "") or author_tag.get_text(" ", strip=True)
            body_text = _clean_body_text(response.text, snippet_limit)
            credential_terms = ["phd", "md", "professor", "doctor", "researcher", "engineer", "cpa", "attorney", "lawyer", "mba", "msc"]
            author_credentials_present = any(re.search(rf"\b{re.escape(term)}\b", (author_text + " " + body_text).lower()) for term in credential_terms)
            references_present = bool(soup.find_all("cite")) or any(token in body_text.lower() for token in ["references", "sources", "bibliography", "works cited"])

            og_title_el = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
            og_desc_el = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "og:description"})
            og_img_el = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
            twitter_img_el = soup.find("meta", attrs={"name": "twitter:image"}) or soup.find("meta", property="twitter:image")
            site_name_el = soup.find("meta", property="og:site_name") or soup.find("meta", attrs={"name": "og:site_name"})
            open_graph_title = og_title_el.get("content", "").strip() if og_title_el else ""
            open_graph_description = og_desc_el.get("content", "").strip() if og_desc_el else ""
            open_graph_image = og_img_el.get("content", "").strip() if og_img_el else ""
            twitter_card_image = twitter_img_el.get("content", "").strip() if twitter_img_el else ""
            site_name_present = site_name_el is not None

            has_open_graph = any(soup.find_all("meta", property=lambda p: p and p.startswith("og:")))
            has_twitter_cards = bool(soup.find_all("meta", attrs={"name": lambda n: n and n.startswith("twitter:")}))
            favicon_tag = soup.find("link", rel=lambda r: r and "icon" in str(r).lower())
            favicon_present = favicon_tag is not None

            aria_label_elements = soup.find_all(lambda t: t.has_attr("aria-label") or t.has_attr("aria-labelledby"))
            aria_labels_present = len(aria_label_elements) > 0
            landmark_tags = ["main", "nav", "header", "footer", "aside", "section", "article"]
            landmark_roles = ["main", "navigation", "banner", "contentinfo", "aside", "search", "complementary"]
            has_landmark_tags = any(soup.find(t) for t in landmark_tags)
            has_landmark_roles = any(soup.find(attrs={"role": role}) for role in landmark_roles)
            aria_landmarks_present = has_landmark_tags or has_landmark_roles
            form_inputs = soup.find_all("input")
            form_labels = soup.find_all("label")
            form_labels_present = False
            if form_inputs:
                input_ids = {inp.get("id") for inp in form_inputs if inp.get("id")}
                label_fors = {lab.get("for") for lab in form_labels if lab.get("for")}
                form_labels_present = bool(input_ids.intersection(label_fors)) or len(form_labels) >= len(form_inputs) * 0.5 or any(inp.has_attr("aria-label") or inp.has_attr("placeholder") for inp in form_inputs)

            list_semantics_invalid_count = sum(1 for li in soup.find_all("li") if not li.parent or li.parent.name not in ["ul", "ol", "menu"])
            table_semantics_invalid_count = sum(1 for table in soup.find_all("table") if not table.find("tr"))
            button_semantics_invalid_count = sum(1 for a in soup.find_all("a") if a.get("href", "").strip() in ["#", "javascript:void(0);", "javascript:void(0)"] and not a.has_attr("role"))

            all_links = soup.find_all("a", href=True)
            base_domain = parsed_final.netloc
            internal_count = 0
            external_count = 0
            broken_internal_links = 0
            broken_external_links = 0
            has_about = has_contact = has_privacy = has_faq_link = False
            anchor_texts: list[str] = []
            generic_anchor_count = 0
            hub_page_links = money_page_links = deep_page_links = nav_links = footer_links = 0
            money_tokens = ["/pricing", "/checkout", "/buy", "/product", "/services", "/shop", "/store", "/plan"]
            hub_tokens = ["/blog", "/resources", "/category", "/hub", "/guides", "/learn"]
            nav_container = soup.find(["nav", "header"]) or soup.find(class_=lambda c: c and any(x in c.lower() for x in ["nav", "menu", "header"]))
            footer_container = soup.find("footer") or soup.find(class_=lambda c: c and "footer" in c.lower())

            for link in all_links:
                href = link["href"].strip()
                href_lower = href.lower()
                text = link.get_text(" ", strip=True)
                text_lower = text.lower()
                parsed_href = urlparse(href)
                is_special = href_lower.startswith(("mailto:", "tel:", "javascript:"))
                is_internal = not is_special and (href.startswith(("/", "./", "../", "#")) or parsed_href.netloc in ["", base_domain])
                if text:
                    anchor_texts.append(text_lower)
                    if text_lower in ["click here", "read more", "learn more", "link", "go", "more", "view"]:
                        generic_anchor_count += 1
                if nav_container and link in nav_container.find_all("a"):
                    nav_links += 1
                if footer_container and link in footer_container.find_all("a"):
                    footer_links += 1
                if is_internal:
                    internal_count += 1
                    if href_lower in ["", "#", "javascript:void(0)", "javascript:void(0);"]:
                        broken_internal_links += 1
                    if any(token in href_lower for token in money_tokens):
                        money_page_links += 1
                    elif any(token in href_lower for token in hub_tokens):
                        hub_page_links += 1
                    elif len([seg for seg in parsed_href.path.split("/") if seg]) >= 3:
                        deep_page_links += 1
                else:
                    external_count += 1
                    if href_lower in ["", "#", "http://", "https://"] or "example.com" in href_lower:
                        broken_external_links += 1
                if "about" in href_lower or "about" in text_lower:
                    has_about = True
                if "contact" in href_lower or "contact" in text_lower or "support" in href_lower:
                    has_contact = True
                if "privacy" in href_lower or "policy" in text_lower or "terms" in text_lower:
                    has_privacy = True
                if "faq" in href_lower or "faq" in text_lower:
                    has_faq_link = True

            unique_anchor_count = len(set(anchor_texts))
            total_anchor_count = len(anchor_texts)
            generic_ratio = generic_anchor_count / max(1, total_anchor_count)
            exact_match_anchor_overuse = "Low Risk"
            if generic_ratio > 0.4:
                exact_match_anchor_overuse = "High Overuse Risk"
            elif generic_ratio > 0.2:
                exact_match_anchor_overuse = "Medium Risk"
            internal_link_context_quality = _clamp_score((1 - generic_ratio) * 100) if total_anchor_count else 0
            navigation_density = round(nav_links / max(1, total_anchor_count), 3)
            footer_link_bloat = "Critical Bloat" if footer_links > 50 else "Excessive Linkage" if footer_links > 25 else "Normal"
            orphan_page_risk = "High Structural Isolation Risk" if internal_count <= 2 else "Isolated Node Hazard" if internal_count <= 5 else "Low Risk"
            deep_page_discoverability = _clamp_score((deep_page_links / max(1, internal_count)) * 100)

            raw_visible_text = _norm_text(soup.get_text(separator=" ", strip=True))
            word_count = len(raw_visible_text.split())
            total_sentences = max(1, len([s for s in re.split(r"[.!?]+\s*", raw_visible_text) if s.strip()]))
            avg_sentence_length = round(word_count / max(1, total_sentences), 1)

            robots_element = soup.find("meta", attrs={"name": "robots"})
            robots_content = robots_element["content"].strip() if robots_element and robots_element.has_attr("content") else "None detected"
            viewport_element = soup.find("meta", attrs={"name": "viewport"})
            viewport_content = viewport_element["content"].strip() if viewport_element and viewport_element.has_attr("content") else None
            mobile_friendly_flag = bool(viewport_content and ("width=device-width" in viewport_content.lower() or "initial-scale" in viewport_content.lower()))

            schema_blocks = soup.find_all("script", type="application/ld+json")
            detected_schemas: list[str] = []
            valid_schemas_count = 0
            for block in schema_blocks:
                try:
                    if block.string:
                        data = json.loads(block.string)
                        valid_schemas_count += 1
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if isinstance(item, dict):
                                if "@graph" in item and isinstance(item["@graph"], list):
                                    for graph_item in item["@graph"]:
                                        if isinstance(graph_item, dict):
                                            detected_schemas.append(str(graph_item.get("@type", "Unknown context type")))
                                else:
                                    detected_schemas.append(str(item.get("@type", "Unknown context type")))
                except Exception:
                    continue
            schema_count = len(schema_blocks)
            schema_validity = "No Schema Detected" if schema_count == 0 else "Valid" if valid_schemas_count == schema_count else "Partially Invalid"

            has_breadcrumbs = any([
                soup.find(class_=lambda c: c and "breadcrumb" in c.lower()),
                soup.find(id=lambda i: i and "breadcrumb" in i.lower()),
                soup.find("nav", attrs={"aria-label": lambda a: a and "breadcrumb" in a.lower()}),
                "BreadcrumbList" in detected_schemas,
            ])
            has_faq_section = any([
                has_faq_link,
                "FAQPage" in detected_schemas,
                any("faq" in str(h).lower() for h in soup.find_all(["h2", "h3", "h4"])),
            ])

            is_https = final_url.lower().startswith("https://")
            has_query_strings = bool(urlparse(final_url).query)
            cta_keywords = ["sign up", "buy now", "subscribe", "contact us", "get started", "demo", "register", "add to cart", "checkout"]
            cta_presence = any(any(kw in el.get_text(" ", strip=True).lower() for kw in cta_keywords) for el in soup.find_all(["a", "button"]))
            trust_keywords = ["guarantee", "testimonial", "review", "secure", "safe", "privacy verified", "trustpilot", "certified"]
            trust_signal_presence = any(kw in raw_visible_text.lower() for kw in trust_keywords) or is_https

            indexable_flag = True
            if status_code >= 400 or robots_txt_blocks_page:
                indexable_flag = False
            elif robots_content != "None detected" and "noindex" in robots_content.lower():
                indexable_flag = False
            elif x_robots_tag_header and "noindex" in x_robots_tag_header.lower():
                indexable_flag = False

            title_length_chars = 0 if title_tag == "Missing" else len(title_tag)
            meta_length_chars = 0 if meta_desc == "Missing" else len(meta_desc)
            title_uniqueness = _uniqueness_label(title_tag)
            meta_uniqueness = _uniqueness_label(meta_desc)

            scraped = {
                "url": url,
                "status_code": status_code,
                "final_url": final_url,
                "redirect_chain": redirect_chain,
                "redirect_count": redirect_count,
                "content_type": content_type,
                "x_robots_tag_header": x_robots_tag_header,
                "robots_txt_present": robots_txt_present,
                "robots_txt_blocks_page": robots_txt_blocks_page,
                "sitemap_present": sitemap_present,
                "sitemap_urls": sitemap_urls,
                "indexable_flag": indexable_flag,
                "canonical_url": canonical_url,
                "canonical_points_to_self": canonical_points_to_self,
                "canonical_status_code": canonical_status_code,
                "canonical_mismatch": canonical_mismatch,
                "multiple_canonicals": multiple_canonicals,
                "canonical_chain_length": canonical_chain_length,
                "parameterized_duplicate_risk": parameterized_duplicate_risk,
                "html_lang": html_lang,
                "hreflang_present": hreflang_present,
                "hreflang_types": hreflang_types,
                "hreflang_errors": hreflang_errors,
                "source_language": source_language,
                "scraped_publication_date": publication_date,
                "scraped_last_modified_date": last_modified_date,
                "scraped_author_present": author_present,
                "scraped_references_present": references_present,
                "publication_date": publication_date,
                "last_modified_date": last_modified_date,
                "author_present": author_present,
                "author_credentials_present": author_credentials_present,
                "references_present": references_present,
                "scraped_title_length_chars": title_length_chars,
                "scraped_meta_length_chars": meta_length_chars,
                "scraped_open_graph_title": open_graph_title,
                "scraped_open_graph_description": open_graph_description,
                "scraped_open_graph_image": open_graph_image,
                "scraped_twitter_card_image": twitter_card_image,
                "scraped_site_name_present": site_name_present,
                "title_length_chars": title_length_chars,
                "title_uniqueness": title_uniqueness,
                "meta_length_chars": meta_length_chars,
                "meta_uniqueness": meta_uniqueness,
                "open_graph_title": open_graph_title,
                "open_graph_description": open_graph_description,
                "open_graph_image": open_graph_image,
                "twitter_card_image": twitter_card_image,
                "site_name_present": site_name_present,
                "scraped_aria_labels_present": aria_labels_present,
                "scraped_aria_landmarks_present": aria_landmarks_present,
                "scraped_form_labels_present": form_labels_present,
                "scraped_list_semantics_invalid_count": list_semantics_invalid_count,
                "scraped_table_semantics_invalid_count": table_semantics_invalid_count,
                "scraped_button_semantics_invalid_count": button_semantics_invalid_count,
                "aria_labels_present": aria_labels_present,
                "aria_landmarks_present": aria_landmarks_present,
                "form_labels_present": form_labels_present,
                "button_semantics_valid": _button_semantics_label(button_semantics_invalid_count, len(all_links)),
                "list_semantics_valid": "Valid" if list_semantics_invalid_count == 0 else "Invalid",
                "table_semantics_valid": "Valid" if table_semantics_invalid_count == 0 else "Invalid",
                "landmark_structure_quality": _clamp_score((35 if has_landmark_tags else 0) + (25 if has_landmark_roles else 0) + (20 if aria_labels_present else 0) + (20 if aria_landmarks_present else 0)),
                "contrast_risk_flag": "Low" if aria_labels_present and aria_landmarks_present else "Medium",
                "scraped_anchor_text_unique_count": unique_anchor_count,
                "scraped_exact_match_anchor_overuse": exact_match_anchor_overuse,
                "scraped_internal_link_context_quality": internal_link_context_quality,
                "scraped_orphan_page_risk": orphan_page_risk,
                "scraped_hub_page_links": hub_page_links,
                "scraped_money_page_links": money_page_links,
                "scraped_deep_page_discoverability": deep_page_discoverability,
                "scraped_navigation_density": navigation_density,
                "scraped_footer_link_bloat": footer_link_bloat,
                "scraped_broken_external_links": broken_external_links,
                "anchor_text_unique_count": unique_anchor_count,
                "exact_match_anchor_overuse": exact_match_anchor_overuse,
                "internal_link_context_quality": internal_link_context_quality,
                "orphan_page_risk": orphan_page_risk,
                "hub_page_links": hub_page_links,
                "money_page_links": money_page_links,
                "deep_page_discoverability": deep_page_discoverability,
                "navigation_density": navigation_density,
                "footer_link_bloat": footer_link_bloat,
                "broken_external_links": broken_external_links,
                "title": title_tag,
                "meta_description": meta_desc,
                "word_count": word_count,
                "heading_counts": heading_counts,
                "fallback_heading_candidates": fallback_heading_candidates,
                "h1_count": len(h1_tags),
                "h1_contents": h1_tags if h1_tags else ["Missing"],
                "heading_semantics_valid": _heading_semantics_label(heading_counts, len(h1_tags)),
                "total_images": total_images,
                "images_missing_alt": images_missing_alt,
                "lazy_loading_used": lazy_loading_used,
                "unoptimized_image_formats": unoptimized_image_formats,
                "alt_quality_score": _clamp_score((1 - images_missing_alt / max(1, total_images)) * 100),
                "total_links": len(all_links),
                "internal_links": internal_count,
                "external_links": external_count,
                "broken_internal_links": broken_internal_links,
                "schema_count": schema_count,
                "detected_schema_types": detected_schemas if detected_schemas else ["None Detected"],
                "schema_validity": schema_validity,
                "open_graph_present": has_open_graph,
                "twitter_cards_present": has_twitter_cards,
                "favicon_present": favicon_present,
                "has_about_page": has_about,
                "has_contact_page": has_contact,
                "has_privacy_policy": has_privacy,
                "has_faq_section": has_faq_section,
                "has_breadcrumbs": has_breadcrumbs,
                "mobile_friendly_flag": mobile_friendly_flag,
                "cta_presence": cta_presence,
                "trust_signal_presence": trust_signal_presence,
                "has_open_graph": has_open_graph,
                "has_twitter_cards": has_twitter_cards,
                "meta_robots": robots_content,
                "has_mobile_viewport": viewport_content is not None,
                "viewport_string": viewport_content or "Missing",
                "response_time_sec": response_time_sec,
                "page_size_kb": page_size_kb,
                "is_https": is_https,
                "url_length": len(final_url),
                "has_query_strings": has_query_strings,
                "query_params": parse_qs(parsed_final.query),
                "avg_sentence_length": avg_sentence_length,
                "total_sentences": total_sentences,
                "body_context_snippet": body_text,
            }

            scraped = _semantic_enrichment(scraped)

            if enable_js_audit:
                js_signals = scrape_js_specific_signals(
                    final_url,
                    raw_scraped=scraped,
                    timeout=float(resolved_js_audit_timeout),
                )
                scraped.update(js_signals)
                scraped["js_rendering_risk"] = _js_rendering_risk_label(scraped)
                scraped["javascript_rendering_analysis"] = _javascript_rendering_summary(scraped)
            else:
                scraped.setdefault("js_audit_checked", False)
                scraped.setdefault("js_audit_available", False)
                scraped.setdefault("js_rendering_risk", "Not checked")

            scraped["title_keyword_position"] = _keyword_position(title_tag, "", scraped.get("primary_topic", ""))
            scraped["snippet_ctr_potential"] = _snippet_ctr_score(
                title_length_chars,
                meta_length_chars,
                has_open_graph,
                favicon_present,
                title_uniqueness,
                meta_uniqueness,
            )

            logger.info("Scraped %s — SEO features processed successfully.", url)
            return scraped

    except httpx.TimeoutException:
        logger.warning("Scrape timed out for %s", url)
        return {"error": f"Request timed out after {timeout:.0f}s"}
    except httpx.TooManyRedirects:
        logger.warning("Too many redirects for %s", url)
        return {"error": "Too many redirects - check the URL"}
    except httpx.RequestError as exc:
        logger.warning("Network error for %s: %s", url, type(exc).__name__)
        return {"error": f"Network error: {type(exc).__name__}"}
    except Exception as exc:
        logger.exception("Unexpected scrape failure for %s", url)
        return {"error": f"Unexpected scrape error: {type(exc).__name__}"}


# ---------------------------------------------------------------------------
# Deterministic report builder
# ---------------------------------------------------------------------------
def _metric_percent(good: int, total: int) -> int:
    if total <= 0:
        return 100
    return _clamp_score(good / total * 100)


def _score_technical(scraped: dict) -> int:
    score = 100
    if not scraped.get("indexable_flag", True):
        score -= 35
    if not scraped.get("is_https", False):
        score -= 15
    if int(scraped.get("status_code", 0) or 0) >= 400:
        score -= 25
    if float(scraped.get("response_time_sec", 0) or 0) > 1.5:
        score -= 10
    if float(scraped.get("page_size_kb", 0) or 0) > 3000:
        score -= 10
    if int(scraped.get("schema_count", 0) or 0) == 0:
        score -= 10
    if scraped.get("canonical_mismatch") or scraped.get("multiple_canonicals"):
        score -= 10
    if scraped.get("hreflang_errors"):
        score -= 5
    return _clamp_score(score, 1, 100)


def _score_content(scraped: dict) -> int:
    score = 100
    title_len = int(scraped.get("title_length_chars", 0) or 0)
    meta_len = int(scraped.get("meta_length_chars", 0) or 0)
    if title_len == 0 or title_len < 30 or title_len > 70:
        score -= 15
    if meta_len == 0 or meta_len < 80 or meta_len > 180:
        score -= 15
    if int(scraped.get("h1_count", 0) or 0) != 1:
        score -= 15
    if int(scraped.get("word_count", 0) or 0) < 300:
        score -= 20
    if scraped.get("keyword_stuffing_risk") == "High":
        score -= 15
    if scraped.get("duplicate_content_risk") == "High":
        score -= 15
    return _clamp_score(score, 1, 100)


def _score_ux(scraped: dict) -> int:
    score = 100
    if not scraped.get("mobile_friendly_flag"):
        score -= 20
    if not scraped.get("has_mobile_viewport"):
        score -= 15
    if int(scraped.get("images_missing_alt", 0) or 0) > 0:
        score -= min(20, int(scraped.get("images_missing_alt", 0) or 0) * 4)
    if not scraped.get("has_breadcrumbs"):
        score -= 5
    if not scraped.get("aria_landmarks_present"):
        score -= 10
    if not scraped.get("form_labels_present") and "input" in str(scraped.get("body_context_snippet", "")).lower():
        score -= 5
    return _clamp_score(score, 1, 100)


def _title_suggestion(scraped: dict, opts: dict) -> str:
    primary = opts.get("focus_keyword") or scraped.get("primary_topic") or scraped.get("title") or "Primary Topic"
    title = scraped.get("title", "")
    if title and title != "Missing" and 45 <= len(title) <= 60:
        return title
    return f"{primary} | Expert Guide & Solutions"[:60]


def _meta_suggestion(scraped: dict) -> str:
    primary = scraped.get("primary_topic") or "this topic"
    return f"Explore {primary} with clear insights, technical guidance, and practical next steps. Start improving your page today."[:155]


def _action_plan(scraped: dict) -> str:
    high: list[str] = []
    medium: list[str] = []
    low: list[str] = []

    if not scraped.get("indexable_flag", True):
        high.append("Resolve indexability blockers by reviewing robots.txt, meta robots, X-Robots-Tag, status code, and canonical configuration.")
    if int(scraped.get("h1_count", 0) or 0) != 1:
        high.append("Add exactly one descriptive H1 that clearly states the page topic and aligns with the target search intent.")
    if scraped.get("title") == "Missing" or int(scraped.get("title_length_chars", 0) or 0) < 30:
        high.append("Rewrite the title tag so it is descriptive, unique, and approximately 50-60 characters.")
    if scraped.get("meta_description") == "Missing" or int(scraped.get("meta_length_chars", 0) or 0) < 80:
        high.append("Write a compelling meta description of roughly 120-155 characters with a clear value proposition.")

    if scraped.get("js_audit_available"):
        if scraped.get("js_content_dependency") == "High":
            high.append("Reduce JavaScript dependency for critical SEO content by server-rendering or pre-rendering the main copy, H1, internal links, and key metadata.")
        if any([
            scraped.get("title_changed_after_render"),
            scraped.get("meta_changed_after_render"),
            scraped.get("canonical_changed_after_render"),
            scraped.get("robots_changed_after_render"),
        ]):
            high.append("Stabilize SEO metadata so title, meta description, canonical, and robots directives do not change unexpectedly after JavaScript rendering.")
        if not scraped.get("above_fold_h1_visible", True):
            medium.append("Make the primary H1 visible above the fold so users and crawlers receive the page topic immediately after render.")
        if not scraped.get("above_fold_primary_cta_visible", True):
            low.append("Add or improve a visible above-the-fold primary CTA to improve conversion clarity for organic visitors.")
        if int(scraped.get("js_console_error_count", 0) or 0) > 0:
            medium.append(f"Resolve {scraped.get('js_console_error_count')} JavaScript console error(s) detected during browser rendering because they may affect hydration, tracking, or content visibility.")

    if int(scraped.get("images_missing_alt", 0) or 0) > 0:
        medium.append(f"Add descriptive alt text to {scraped.get('images_missing_alt')} image(s) to improve accessibility and image search context.")
    if int(scraped.get("schema_count", 0) or 0) == 0:
        medium.append("Add relevant JSON-LD structured data such as Organization, WebPage, Article, Product, FAQPage, or BreadcrumbList depending on page type.")
    if float(scraped.get("response_time_sec", 0) or 0) > 1.5:
        medium.append("Investigate server latency and rendering bottlenecks because response time exceeds the 1.5 second warning threshold.")
    if float(scraped.get("page_size_kb", 0) or 0) > 3000:
        medium.append("Reduce page weight by compressing images, removing unused scripts, and enabling aggressive caching.")
    if scraped.get("canonical_mismatch") or scraped.get("multiple_canonicals"):
        medium.append("Fix canonical configuration so the page has one clear canonical destination with a healthy status code.")

    if not scraped.get("has_breadcrumbs"):
        low.append("Consider adding breadcrumb navigation and BreadcrumbList schema for clearer page hierarchy.")
    if not scraped.get("has_open_graph") or not scraped.get("has_twitter_cards"):
        low.append("Complete Open Graph and Twitter Card metadata to improve link-preview quality on social platforms.")
    if not scraped.get("has_about_page") or not scraped.get("has_contact_page") or not scraped.get("has_privacy_policy"):
        low.append("Strengthen trust by ensuring About, Contact, and Privacy/Terms pages are discoverable from the audited page.")

    if not high:
        high.append("No critical blockers were detected from the available scrape data.")
    if not medium:
        medium.append("No medium-priority improvements were detected from the available scrape data.")
    if not low:
        low.append("No low-priority refinements were detected from the available scrape data.")

    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    return f"### [HIGH PRIORITY]\n{bullets(high)}\n\n### [MEDIUM PRIORITY]\n{bullets(medium)}\n\n### [LOW PRIORITY]\n{bullets(low)}"


def _build_deterministic_report(scraped_data: dict, options: dict | None = None) -> SEOAuditReport:
    opts = _resolve_audit_options(options)
    scraped = _semantic_enrichment(dict(scraped_data), opts.get("focus_keyword", ""))

    title = scraped.get("title", "Missing")
    meta = scraped.get("meta_description", "Missing")
    title_len = int(scraped.get("title_length_chars", 0) or 0)
    meta_len = int(scraped.get("meta_length_chars", 0) or 0)
    total_images = int(scraped.get("total_images", 0) or 0)
    missing_alt = int(scraped.get("images_missing_alt", 0) or 0)
    alt_score = _metric_percent(total_images - missing_alt, total_images)
    technical_score = _score_technical(scraped)
    content_score = _score_content(scraped)
    ux_score = _score_ux(scraped)
    overall_score = _clamp_score(technical_score * 0.4 + content_score * 0.35 + ux_score * 0.25, 1, 100)

    heading_counts = scraped.get("heading_counts", {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0})
    if not isinstance(heading_counts, dict):
        heading_counts = {"h1": 0, "h2": 0, "h3": 0, "h4": 0, "h5": 0, "h6": 0}

    javascript_rendering_analysis = _javascript_rendering_summary(scraped)
    js_rendering_risk = _js_rendering_risk_label(scraped)

    data = {
        "overall_score": overall_score,
        "category_scores": {"Technical": technical_score, "Content": content_score, "UX": ux_score},
        "title_issue": f"The title is '{title}'. It has {title_len} characters; ideal title tags are usually descriptive and roughly 50-60 characters. Keyword position is {scraped.get('title_keyword_position', 'Missing')}.",
        "suggested_title": _title_suggestion(scraped, opts),
        "meta_issue": f"The meta description is '{meta}'. It has {meta_len} characters; ideal descriptions usually sit around 120-155 characters with a clear value proposition and CTA.",
        "suggested_meta": _meta_suggestion(scraped),
        "image_alt_analysis": f"The page has {total_images} image(s), with {missing_alt} missing alt text. Alt coverage is {alt_score}/100, affecting accessibility and image-search context.",
        "image_alt_quality": alt_score,
        "image_size_optimization": _clamp_score(100 - int(scraped.get("unoptimized_image_formats", 0) or 0) * 10),
        "link_strategy_analysis": f"The page contains {scraped.get('total_links', 0)} raw HTML link(s): {scraped.get('internal_links', 0)} internal and {scraped.get('external_links', 0)} external. Internal link context quality is {scraped.get('internal_link_context_quality', 0)}/100. Browser rendering found {scraped.get('rendered_total_links', 0)} rendered link(s) and {scraped.get('js_added_links', 0)} link(s) added after JavaScript execution.",
        "media_and_links_detailed_analysis": f"Media optimization shows {scraped.get('lazy_loading_used', 0)} lazy-loaded image(s) and {scraped.get('unoptimized_image_formats', 0)} potentially legacy-format image(s). Footer bloat status is {scraped.get('footer_link_bloat', 'Normal')}. The rendered browser pass loaded {scraped.get('image_resource_count', 0)} image resource(s), {scraped.get('js_resource_count', 0)} JavaScript resource(s), and {scraped.get('third_party_resource_count', 0)} third-party resource(s) when available.",
        "anchor_text_quality": _clamp_score(scraped.get("internal_link_context_quality", 0)),
        "internal_link_relevance_score": _clamp_score(scraped.get("internal_link_context_quality", 0)),
        "heading_counts": {f"h{i}": int(heading_counts.get(f"h{i}", 0) or 0) for i in range(1, 7)},
        "heading_hierarchy_analysis": f"Raw heading counts are H1={heading_counts.get('h1', 0)}, H2={heading_counts.get('h2', 0)}, H3={heading_counts.get('h3', 0)}, H4={heading_counts.get('h4', 0)}, H5={heading_counts.get('h5', 0)}, H6={heading_counts.get('h6', 0)}. Semantic status: {scraped.get('heading_semantics_valid', 'Unknown')}. The rendered DOM contains {scraped.get('rendered_h1_count', 0)} H1 element(s), and above-the-fold H1 visibility is {scraped.get('above_fold_h1_visible', False)} when JavaScript auditing is available.",
        "content_depth_analysis": f"The raw HTML has approximately {scraped.get('word_count', 0)} words, {scraped.get('total_sentences', 0)} sentences, and an average sentence length of {scraped.get('avg_sentence_length', 0)} words. Thin content flag is {scraped.get('thin_content_flag', False)}. Rendered word count is {scraped.get('rendered_word_count', 0)}, with a JavaScript-rendered content delta of {scraped.get('rendered_word_delta', 0)} word(s) when available.",
        "social_tags_analysis": f"Open Graph is {_bool_label(scraped.get('has_open_graph', False))}, Twitter Cards are {_bool_label(scraped.get('has_twitter_cards', False))}, favicon is {_bool_label(scraped.get('favicon_present', False))}, and site name metadata is {_bool_label(scraped.get('site_name_present', False))}.",
        "indexing_directives_analysis": f"Indexable flag is {scraped.get('indexable_flag', True)}. Canonical URL is {scraped.get('canonical_url', 'Missing')}; canonical self-reference is {scraped.get('canonical_points_to_self', False)}. Robots meta is {scraped.get('meta_robots', 'None detected')}; hreflang errors: {scraped.get('hreflang_errors', [])}. JavaScript rendering risk is {js_rendering_risk}; metadata changed after render: title={scraped.get('title_changed_after_render', False)}, meta={scraped.get('meta_changed_after_render', False)}, canonical={scraped.get('canonical_changed_after_render', False)}, robots={scraped.get('robots_changed_after_render', False)}.",
        "schema_structured_data_analysis": f"The raw HTML exposes {scraped.get('schema_count', 0)} JSON-LD block(s). Detected raw schema types: {scraped.get('detected_schema_types', ['None Detected'])}. Schema validity status: {scraped.get('schema_validity', 'Unknown')}. The rendered DOM exposes {scraped.get('rendered_schema_count', 0)} JSON-LD block(s), with schema_added_by_js={scraped.get('schema_added_by_js', False)} when JavaScript auditing is available.",
        "security_performance_analysis": f"HTTPS is {_bool_label(scraped.get('is_https', False))}. Response time is {float(scraped.get('response_time_sec', 0) or 0):.3f}s and page size is {float(scraped.get('page_size_kb', 0) or 0):.1f} KB. Status code is {scraped.get('status_code', 0)} with {scraped.get('redirect_count', 0)} redirect(s). Browser rendering loaded approximately {scraped.get('total_transfer_size_kb', 0)} KB of resources and reported {scraped.get('failed_request_count', 0)} failed request(s) when JavaScript auditing is available.",
        "url_structure_analysis": f"The final URL is {scraped.get('final_url', scraped.get('url', ''))}. URL length is {scraped.get('url_length', 0)} characters and query strings are {_bool_label(scraped.get('has_query_strings', False))}.",
        "eeat_authority_analysis": f"About page: {_bool_label(scraped.get('has_about_page', False))}; contact page: {_bool_label(scraped.get('has_contact_page', False))}; privacy policy: {_bool_label(scraped.get('has_privacy_policy', False))}; author: {_bool_label(scraped.get('author_present', False))}; references: {_bool_label(scraped.get('references_present', False))}.",
        "readability_user_experience_analysis": f"Readability grade level is {scraped.get('readability_grade_level', 'Unknown')}. Average sentence length is {scraped.get('avg_sentence_length', 0)} words and mobile-friendly status is {_bool_label(scraped.get('mobile_friendly_flag', False))}. Above-the-fold word count is {scraped.get('above_fold_word_count', 0)}, H1 visibility is {scraped.get('above_fold_h1_visible', False)}, and CTA visibility is {scraped.get('above_fold_primary_cta_visible', False)} when browser rendering data is available.",
        "faq_breadcrumbs_analysis": f"FAQ section detected: {_bool_label(scraped.get('has_faq_section', False))}. Breadcrumbs detected: {_bool_label(scraped.get('has_breadcrumbs', False))}.",
        "content_quality_analysis": f"Primary topic is '{scraped.get('primary_topic', '')}'. Search intent is {scraped.get('search_intent_type', '')}. Duplicate content risk is {scraped.get('duplicate_content_risk', 'Low')} and keyword stuffing risk is {scraped.get('keyword_stuffing_risk', 'Low')}.",
        "content_uniqueness_score": _clamp_score(scraped.get("content_originality_score", 0)),
        "search_intent_match": _clamp_score(80 if scraped.get("search_intent_type") else 50),
        "topic_coverage_score": _clamp_score(scraped.get("topical_completeness", 0)),
        "readability_score": 75 if scraped.get("readability_grade_level") != "Unknown" else 50,
        "structured_data_discoverability_score": _clamp_score(40 + int(scraped.get("schema_count", 0) or 0) * 15),
        "trust_signals_conversion_score": _clamp_score(scraped.get("source_quality_score", 0)),
        "trust_meta_structural_analysis": f"Source quality score is {scraped.get('source_quality_score', 0)}/100. CTA presence is {_bool_label(scraped.get('cta_presence', False))}; trust signal presence is {_bool_label(scraped.get('trust_signal_presence', False))}.",
        "title_length_chars": title_len,
        "title_keyword_position": scraped.get("title_keyword_position", "Missing"),
        "meta_length_chars": meta_len,
        "snippet_ctr_potential": _clamp_score(scraped.get("snippet_ctr_potential", 0)),
        "title_uniqueness": scraped.get("title_uniqueness", "Low"),
        "meta_uniqueness": scraped.get("meta_uniqueness", "Low"),
        "open_graph_title": scraped.get("open_graph_title", ""),
        "open_graph_description": scraped.get("open_graph_description", ""),
        "open_graph_image": scraped.get("open_graph_image", ""),
        "twitter_card_image": scraped.get("twitter_card_image", ""),
        "favicon_present": bool(scraped.get("favicon_present", False)),
        "site_name_present": bool(scraped.get("site_name_present", False)),
        "aria_labels_present": bool(scraped.get("aria_labels_present", False)),
        "aria_landmarks_present": bool(scraped.get("aria_landmarks_present", False)),
        "button_semantics_valid": scraped.get("button_semantics_valid", "Valid"),
        "list_semantics_valid": scraped.get("list_semantics_valid", "Valid"),
        "table_semantics_valid": scraped.get("table_semantics_valid", "Valid"),
        "form_labels_present": bool(scraped.get("form_labels_present", False)),
        "alt_quality_score": _clamp_score(scraped.get("alt_quality_score", alt_score)),
        "heading_semantics_valid": scraped.get("heading_semantics_valid", "Valid"),
        "landmark_structure_quality": _clamp_score(scraped.get("landmark_structure_quality", 0)),
        "contrast_risk_flag": scraped.get("contrast_risk_flag", "Low"),
        "anchor_text_unique_count": int(scraped.get("anchor_text_unique_count", 0) or 0),
        "exact_match_anchor_overuse": scraped.get("exact_match_anchor_overuse", "Low Risk"),
        "internal_link_context_quality": _clamp_score(scraped.get("internal_link_context_quality", 0)),
        "orphan_page_risk": scraped.get("orphan_page_risk", "Low Risk"),
        "hub_page_links": int(scraped.get("hub_page_links", 0) or 0),
        "money_page_links": int(scraped.get("money_page_links", 0) or 0),
        "deep_page_discoverability": _clamp_score(scraped.get("deep_page_discoverability", 0)),
        "navigation_density": float(scraped.get("navigation_density", 0.0) or 0.0),
        "footer_link_bloat": scraped.get("footer_link_bloat", "Normal"),
        "broken_external_links": int(scraped.get("broken_external_links", 0) or 0),
        "primary_topic": scraped.get("primary_topic", ""),
        "secondary_topics": scraped.get("secondary_topics", []),
        "search_intent_type": scraped.get("search_intent_type", "Informational"),
        "entity_coverage": scraped.get("entity_coverage", []),
        "topical_completeness": _clamp_score(scraped.get("topical_completeness", 0)),
        "content_freshness": scraped.get("content_freshness", "Unknown"),
        "publication_date": scraped.get("publication_date", "Unknown"),
        "last_modified_date": scraped.get("last_modified_date", "Unknown"),
        "author_present": bool(scraped.get("author_present", False)),
        "author_credentials_present": bool(scraped.get("author_credentials_present", False)),
        "references_present": bool(scraped.get("references_present", False)),
        "source_quality_score": _clamp_score(scraped.get("source_quality_score", 0)),
        "duplicate_content_risk": scraped.get("duplicate_content_risk", "Low"),
        "thin_content_flag": bool(scraped.get("thin_content_flag", False)),
        "keyword_stuffing_risk": scraped.get("keyword_stuffing_risk", "Low"),
        "content_originality_score": _clamp_score(scraped.get("content_originality_score", 0)),
        "readability_grade_level": scraped.get("readability_grade_level", "Unknown"),
        "language_detected": scraped.get("language_detected", "unknown"),
        "javascript_rendering_analysis": javascript_rendering_analysis,
        "js_audit_checked": bool(scraped.get("js_audit_checked", False)),
        "js_audit_available": bool(scraped.get("js_audit_available", False)),
        "js_rendering_risk": js_rendering_risk,
        "js_content_dependency": scraped.get("js_content_dependency", "Not checked"),
        "rendering_gap_score": _clamp_score(scraped.get("rendering_gap_score", 0)),
        "rendered_word_count": int(scraped.get("rendered_word_count", 0) or 0),
        "rendered_word_delta": int(scraped.get("rendered_word_delta", 0) or 0),
        "after_scroll_word_count": int(scraped.get("after_scroll_word_count", 0) or 0),
        "scroll_revealed_word_delta": int(scraped.get("scroll_revealed_word_delta", 0) or 0),
        "rendered_h1_count": int(scraped.get("rendered_h1_count", 0) or 0),
        "rendered_total_links": int(scraped.get("rendered_total_links", 0) or 0),
        "js_added_links": int(scraped.get("js_added_links", 0) or 0),
        "rendered_schema_count": int(scraped.get("rendered_schema_count", 0) or 0),
        "schema_added_by_js": bool(scraped.get("schema_added_by_js", False)),
        "above_fold_word_count": int(scraped.get("above_fold_word_count", 0) or 0),
        "above_fold_h1_visible": bool(scraped.get("above_fold_h1_visible", False)),
        "above_fold_primary_cta_visible": bool(scraped.get("above_fold_primary_cta_visible", False)),
        "title_changed_after_render": bool(scraped.get("title_changed_after_render", False)),
        "meta_changed_after_render": bool(scraped.get("meta_changed_after_render", False)),
        "canonical_changed_after_render": bool(scraped.get("canonical_changed_after_render", False)),
        "robots_changed_after_render": bool(scraped.get("robots_changed_after_render", False)),
        "client_side_redirect_detected": bool(scraped.get("client_side_redirect_detected", False)),
        "js_console_error_count": int(scraped.get("js_console_error_count", 0) or 0),
        "failed_request_count": int(scraped.get("failed_request_count", 0) or 0),
        "action_item_markdown": _action_plan(scraped),
    }
    return SEOAuditReport.model_validate(data)


# ---------------------------------------------------------------------------
# LLM analysis engine
# ---------------------------------------------------------------------------
def _ollama_is_reachable(base_url: str, ping_timeout: float) -> bool:
    try:
        with httpx.Client(timeout=ping_timeout) as client:
            resp = client.get(base_url)
            return resp.status_code < 500
    except Exception:
        return False


def _keyword_directive(options: dict) -> str:
    if options.get("focus_keyword"):
        return f"Target keyword: {options['focus_keyword']}. Evaluate fit in title, meta, headings, body, and semantic topic coverage."
    return "No target keyword was supplied. Infer the dominant topic from the scraped data."


def _secondary_keywords_directive(options: dict) -> str:
    secondary = _safe_text(options.get("secondary_keywords", ""))
    return f"Secondary keywords: {secondary}. Evaluate natural coverage if present." if secondary else ""


def _scoring_severity_directive(options: dict) -> str:
    rigor = options.get("audit_rigor")
    if rigor == "Hyper-Critical Forensic Check (Strict Grading)":
        return "Use strict enterprise grading; penalize minor technical and semantic issues more aggressively."
    if rigor == "Lenient Assessment (Core Indexing Infrastructure Only)":
        return "Use lenient grading; heavily penalize only major indexability, metadata, or security failures."
    return "Use balanced standard SEO grading."


def _output_language_directive(options: dict) -> str:
    language = options.get("output_language", "English")
    if language == "Match site language":
        return "Write narrative values in the detected site language. Keep JSON keys in English."
    return f"Write narrative values in {language}. Keep JSON keys in English."


def _analysis_depth_directive(options: dict) -> str:
    depth = options.get("analysis_depth", "Standard")
    if depth == "Brief":
        return "Use 1 concise sentence per narrative field."
    if depth == "Exhaustive":
        return "Use 3-5 detailed sentences per narrative field, but keep JSON valid."
    return "Use 2-3 specific sentences per narrative field."


def _report_tone_directive(options: dict) -> str:
    tone = options.get("report_tone", "Technical")
    if tone == "Executive Summary":
        return "Use business-impact language suitable for non-technical stakeholders."
    if tone == "Developer-Focused":
        return "Use implementation-oriented language referencing concrete HTML/meta/schema fixes."
    return "Use objective, technical, professional language."


def _apply_body_snippet_limit(scraped_data: dict, body_snippet_chars: int) -> dict:
    data = dict(scraped_data)
    snippet = data.get("body_context_snippet", "")
    if isinstance(snippet, str):
        data["body_context_snippet"] = snippet[:body_snippet_chars]
    return data


def _json_template_from_report(report: SEOAuditReport) -> dict:
    return report.model_dump()


def _validate_llm_output_shape(parsed: dict, json_template: dict) -> tuple[bool, list[str], list[str]]:
    expected_keys = set(json_template.keys())
    actual_keys = set(parsed.keys())
    missing_keys = sorted(expected_keys - actual_keys)
    extra_keys = sorted(actual_keys - expected_keys)
    return len(missing_keys) == 0, missing_keys, extra_keys


def _build_compact_system_prompt(opts: dict, json_template: dict) -> str:
    required_keys = list(json_template.keys())
    return f"""
        You are an enterprise-level professional Technical SEO Director. Return exactly one complete SEOAuditReport JSON object.

        Critical output rules:
        - Do NOT return scraped data. Do NOT summarize the input object.
        - Every top-level key in the schema must appear exactly once.
        - Do not add extra keys. Do not omit keys. Do not use markdown fences.
        - Use only supplied evidence. Do not invent rankings, traffic, backlinks, or off-page facts.
        - {_output_language_directive(opts)}
        - {_analysis_depth_directive(opts)}
        - {_report_tone_directive(opts)}
        - {_scoring_severity_directive(opts)}
        - {_keyword_directive(opts)}
        - {_secondary_keywords_directive(opts)}

        Required top-level keys:
        {json.dumps(required_keys, ensure_ascii=False)}

        Narrative fields that MUST be plain strings, never objects or arrays:
        {json.dumps(sorted(NARRATIVE_FIELDS), ensure_ascii=False)}

        For these narrative fields:
        - Return a readable paragraph string.
        - Do not return nested JSON.
        - Do not return dictionaries.
        - Do not return arrays.

        If JavaScript rendering fields are present, use them to explain raw-vs-rendered content gaps, metadata changes after render, JS-added links, rendered schema, above-the-fold visibility, browser console errors, and failed requests. Do not invent browser data when js_audit_available is false.

        Schema/template to fill:
        {json.dumps(json_template, ensure_ascii=False)}

        Use the baseline values when they are already evidence-based. Improve narrative fields and recommendations.
        The output must start with {{"overall_score": ...}}, not with scraped-only fields such as {{"word_count": ...}}.

        action_item_markdown must include exactly:
        ### [HIGH PRIORITY]
        ### [MEDIUM PRIORITY]
        ### [LOW PRIORITY]

        Return only JSON and nothing else.
        """.strip()

def _repair_incomplete_json(
    ollama_chat_url: str,
    model_timeout: float,
    ollama_options: dict,
    bad_output: str,
    json_template: dict,
    missing_keys: list[str],
) -> str:
    repair_prompt = f"""
Your previous JSON was incomplete and missed these keys:
{json.dumps(missing_keys, ensure_ascii=False)}

Rewrite it as one complete JSON object matching this schema exactly:
{json.dumps(json_template, ensure_ascii=False)}

Rules: no markdown, no explanation, no extra keys. Return only JSON.

Previous output:
{bad_output}
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": "You repair incomplete JSON into a required schema."},
            {"role": "user", "content": repair_prompt},
        ],
        "response_format": {"type": "json_object"},
        "options": ollama_options,
    }
    with httpx.Client(timeout=model_timeout) as client:
        response = client.post(ollama_chat_url, json=payload)
        response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

def _humanize_key(key: str) -> str:
    text = re.sub(r"[_\\-]+", " ", str(key)).strip()
    text = re.sub(r"\\s+", " ", text)
    return text[:1].upper() + text[1:] if text else "Field"


def _format_scalar_for_narrative(value: Any) -> str:
    if isinstance(value, bool):
        return "present" if value else "missing"

    if value is None:
        return "not detected"

    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")

    return str(value).strip()


def _narrative_value_to_string(value: Any) -> str:
    """
    Converts LLM-returned dict/list narrative values into readable text.

    This protects string fields such as:
    - social_tags_analysis
    - indexing_directives_analysis
    - schema_structured_data_analysis
    - security_performance_analysis
    - content_quality_analysis
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        parts = []

        for raw_key, raw_value in value.items():
            label = _humanize_key(raw_key)

            if isinstance(raw_value, dict):
                nested_items = [
                    f"{_humanize_key(k)}: {_format_scalar_for_narrative(v)}"
                    for k, v in raw_value.items()
                    if v not in [None, "", [], {}]
                ]

                if nested_items:
                    parts.append(f"{label}: {', '.join(nested_items)}")

            elif isinstance(raw_value, list):
                if not raw_value:
                    continue

                compact_items = [
                    _format_scalar_for_narrative(item)
                    for item in raw_value
                    if item not in [None, "", [], {}]
                ]

                if compact_items:
                    parts.append(f"{label}: {', '.join(compact_items)}")

            else:
                parts.append(f"{label}: {_format_scalar_for_narrative(raw_value)}")

        if not parts:
            return ""

        return ". ".join(parts) + "."

    if isinstance(value, list):
        compact_items = [
            _narrative_value_to_string(item)
            for item in value
            if item not in [None, "", [], {}]
        ]

        compact_items = [item for item in compact_items if item]

        if not compact_items:
            return ""

        return " ".join(compact_items)

    return _format_scalar_for_narrative(value)


def _coerce_llm_field_value(key: str, value: Any) -> Any:
    """
    Coerce LLM output into the expected SEOAuditReport field type.
    Narrative fields must remain strings.
    """

    if key in NARRATIVE_FIELDS:
        return _narrative_value_to_string(value)

    return value

def _merge_llm_report(base: SEOAuditReport, parsed: dict) -> SEOAuditReport:
    """
    Merge valid LLM fields into the deterministic report without letting partial
    JSON erase evidence or break Pydantic validation.

    Important:
    LLMs sometimes return nested objects for narrative fields during exhaustive
    mode. Those fields are strings in SEOAuditReport, so they must be converted
    into readable text before validation.
    """

    merged = base.model_dump()

    for key, value in parsed.items():
        if key not in merged:
            continue

        if key in DETERMINISTIC_FIELDS:
            # Keep deterministic values stable. Only allow LLM for narrative fields.
            continue

        if value in [None, "", [], {}]:
            continue

        coerced_value = _coerce_llm_field_value(key, value)

        if coerced_value in [None, "", [], {}]:
            continue

        merged[key] = coerced_value

    try:
        return SEOAuditReport.model_validate(merged)
    except Exception as exc:
        logger.error("Merged LLM report failed validation after coercion: %s", exc)
        return base

def run_local_seo_audit(scraped_data: dict, options: dict = None) -> SEOAuditReport:
    if not scraped_data or "error" in scraped_data:
        reason = scraped_data.get("error", "Empty scrape result") if scraped_data else "No data"
        return SEOAuditReport(title_issue=f"Audit skipped — {reason}")

    opts = _resolve_audit_options(options)
    scraped_data = _maybe_enrich_with_js_audit(dict(scraped_data), opts)
    scraped_data = _apply_body_snippet_limit(scraped_data, int(opts["body_snippet_chars"]))
    scraped_data = _semantic_enrichment(scraped_data, opts.get("focus_keyword", ""))
    baseline_report = _build_deterministic_report(scraped_data, opts)
    json_template = _json_template_from_report(baseline_report)

    ollama_base_url = OLLAMA_BASE_URL.rstrip("/")
    ollama_chat_url = f"{ollama_base_url}/v1/chat/completions"
    model_timeout = float(opts["model_timeout"])
    ping_timeout = DEFAULT_OLLAMA_PING_TIMEOUT

    if not _ollama_is_reachable(ollama_base_url, ping_timeout):
        logger.warning("Ollama service is not reachable. Returning deterministic report.")
        return baseline_report

    system_prompt = _build_compact_system_prompt(opts, json_template)

    ollama_options = {
        "temperature": float(opts["temperature"]),
        "top_p": float(opts["top_p"]),
        "num_predict": int(opts["max_tokens"]),
        "num_ctx": int(opts["num_ctx"]),
    }
    if opts.get("seed") is not None:
        ollama_options["seed"] = int(opts["seed"])

    # Send a compact payload. Baseline report tells the model the exact output shape.
    model_input = {
        "scraped_data": scraped_data,
        "baseline_report": baseline_report.model_dump(),
    }

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(model_input, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
        "options": ollama_options,
    }

    try:
        with httpx.Client(timeout=model_timeout) as client:
            response = client.post(ollama_chat_url, json=payload)
            response.raise_for_status()
    except Exception as exc:
        logger.error("LLM inference failed: %s", exc)
        return baseline_report

    try:
        raw_content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.error("Unexpected Ollama response structure: %s", exc)
        return baseline_report

    clean_content = _extract_json_object(raw_content)

    try:
        parsed_output = json.loads(clean_content)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", exc)
        logger.error("Raw output: %s", clean_content[:2000])
        return baseline_report

    if not isinstance(parsed_output, dict):
        logger.error("LLM output was JSON but not an object. Returning deterministic report.")
        return baseline_report

    valid_shape, missing_keys, extra_keys = _validate_llm_output_shape(parsed_output, json_template)
    if not valid_shape:
        logger.warning("LLM returned incomplete JSON. Missing %d keys, extra %d keys.", len(missing_keys), len(extra_keys))
        logger.warning("Missing keys preview: %s", missing_keys[:12])

        if opts.get("repair_incomplete_json"):
            try:
                repaired = _repair_incomplete_json(
                    ollama_chat_url=ollama_chat_url,
                    model_timeout=model_timeout,
                    ollama_options=ollama_options,
                    bad_output=clean_content,
                    json_template=json_template,
                    missing_keys=missing_keys,
                )
                repaired_parsed = json.loads(_extract_json_object(repaired))
                repaired_valid, repaired_missing, _ = _validate_llm_output_shape(repaired_parsed, json_template)
                if repaired_valid:
                    return _merge_llm_report(baseline_report, repaired_parsed)
                logger.warning("Repair failed. Still missing keys: %s", repaired_missing[:12])
            except Exception as exc:
                logger.error("Repair pass failed: %s", exc)

        # Important: do not return a blank Pydantic default report. Merge any useful
        # narrative fields from the partial JSON, otherwise return the deterministic report.
        return _merge_llm_report(baseline_report, parsed_output)

    try:
        validated_llm_report = SEOAuditReport.model_validate(parsed_output)
        return _merge_llm_report(baseline_report, validated_llm_report.model_dump())
    except Exception as exc:
        logger.error("Pydantic validation failed after complete-shape check: %s", exc)
        return _merge_llm_report(baseline_report, parsed_output)


