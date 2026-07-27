from __future__ import annotations

import streamlit as st


LANDING_CSS = """
<style>
:root {
    --page: #f2f1ec;
    --surface: #ffffff;
    --ink: #171914;
    --muted: #555a50;
    --line: #cfd2c9;
    --line-dark: #aeb3a7;
    --accent: #a97922;
    --accent-dark: #785617;
    --dark: #1b2118;
    --dark-text: #f7f7f2;
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: auto;
}

body {
    margin: 0;
}

.stApp {
    background: var(--page);
}

.block-container {
    max-width: 100% !important;
    padding: 0 !important;
}

header[data-testid="stHeader"] {
    background: transparent;
}

.seo-landing {
    width: 100%;
    margin: 0;
    background: var(--page);
    color: var(--ink);
    font-family: Arial, Helvetica, sans-serif;
    font-size: 17px;
    line-height: 1.6;
}

.seo-landing * {
    box-sizing: border-box;
}

.seo-landing a {
    color: inherit;
}

.seo-landing h1,
.seo-landing h2,
.seo-landing h3,
.seo-landing p {
    margin-top: 0;
}

.site-nav {
    border-bottom: 1px solid var(--line);
    background: var(--surface);
}

.nav-inner {
    width: min(1120px, calc(100% - 40px));
    min-height: 76px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 28px;
}

.brand {
    margin-right: auto;
    color: var(--ink);
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -0.04em;
    text-decoration: none;
}

.brand-mark {
    display: inline-block;
    width: 13px;
    height: 13px;
    margin-right: 8px;
    border: 3px solid var(--accent);
    vertical-align: 1px;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 22px;
}

.nav-links a {
    color: var(--ink);
    font-size: 16px;
    font-weight: 700;
    text-decoration: none;
}

.nav-links a:hover {
    text-decoration: underline;
    text-underline-offset: 5px;
}

.nav-action {
    display: inline-block;
    padding: 10px 17px;
    border: 2px solid var(--ink);
    background: var(--ink);
    color: #ffffff !important;
    text-decoration: none !important;
}

.nav-action:hover {
    background: var(--accent-dark);
    border-color: var(--accent-dark);
}

.page-section {
    width: min(1120px, calc(100% - 40px));
    margin: 0 auto;
    padding: 88px 0;
}

.section-border {
    border-top: 1px solid var(--line);
}

.hero {
    display: grid;
    grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
    gap: 64px;
    align-items: center;
    padding-top: 92px;
    padding-bottom: 92px;
}

.hero h1 {
    max-width: 760px;
    margin-bottom: 28px;
    font-size: clamp(48px, 7vw, 82px);
    line-height: 0.98;
    letter-spacing: -0.055em;
}

.hero p {
    max-width: 690px;
    margin-bottom: 34px;
    color: var(--muted);
    font-size: 21px;
    line-height: 1.55;
}

.hero-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}

.button {
    display: inline-block;
    min-width: 170px;
    padding: 13px 20px;
    border: 2px solid var(--ink);
    background: var(--ink);
    color: #ffffff !important;
    font-size: 17px;
    font-weight: 800;
    text-align: center;
    text-decoration: none;
}

.button:hover {
    background: var(--accent-dark);
    border-color: var(--accent-dark);
}

.button-secondary {
    background: transparent;
    color: var(--ink) !important;
}

.button-secondary:hover {
    background: var(--surface);
    border-color: var(--ink);
}

.audit-example {
    border: 2px solid var(--ink);
    background: var(--surface);
}

.audit-example-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 22px;
    border-bottom: 2px solid var(--ink);
}

.audit-example-head h2 {
    margin: 0;
    font-size: 24px;
    letter-spacing: -0.03em;
}

.audit-score {
    font-size: 34px;
    font-weight: 800;
}

.audit-list {
    margin: 0;
    padding: 0;
    list-style: none;
}

.audit-list li {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 20px;
    padding: 18px 22px;
    border-bottom: 1px solid var(--line);
    font-size: 17px;
}

.audit-list li:last-child {
    border-bottom: 0;
}

.audit-list strong {
    color: var(--accent-dark);
}

.metric-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    background: var(--surface);
}

.metric {
    min-height: 150px;
    padding: 34px;
    border-right: 1px solid var(--line);
}

.metric:last-child {
    border-right: 0;
}

.metric strong {
    display: block;
    margin-bottom: 8px;
    color: var(--ink);
    font-size: 38px;
    line-height: 1;
}

.metric span {
    color: var(--muted);
    font-size: 17px;
}

.section-heading {
    max-width: 760px;
    margin-bottom: 44px;
}

.section-heading h2 {
    margin-bottom: 18px;
    font-size: clamp(36px, 5vw, 55px);
    line-height: 1.05;
    letter-spacing: -0.045em;
}

.section-heading p {
    margin-bottom: 0;
    color: var(--muted);
    font-size: 20px;
}

.flat-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-top: 1px solid var(--line-dark);
    border-left: 1px solid var(--line-dark);
}

.flat-card {
    min-height: 250px;
    padding: 34px;
    border-right: 1px solid var(--line-dark);
    border-bottom: 1px solid var(--line-dark);
    background: var(--surface);
}

.flat-card h3 {
    margin-bottom: 16px;
    font-size: 27px;
    line-height: 1.2;
    letter-spacing: -0.025em;
}

.flat-card p {
    margin-bottom: 0;
    color: var(--muted);
    font-size: 18px;
}

.score-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 20px;
    padding-bottom: 16px;
    margin-bottom: 18px;
    border-bottom: 4px solid var(--accent);
}

.score-line strong {
    font-size: 30px;
}

.dark-section {
    width: 100%;
    background: var(--dark);
    color: var(--dark-text);
}

.dark-section .page-section {
    padding-top: 88px;
    padding-bottom: 88px;
}

.dark-section .section-heading p {
    color: #d8dbd3;
}

.process-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-top: 1px solid #596052;
    border-left: 1px solid #596052;
}

.process-step {
    min-height: 230px;
    padding: 30px;
    border-right: 1px solid #596052;
    border-bottom: 1px solid #596052;
}

.process-number {
    display: block;
    margin-bottom: 28px;
    color: #d8b66a;
    font-size: 28px;
    font-weight: 800;
}

.process-step h3 {
    margin-bottom: 12px;
    font-size: 25px;
}

.process-step p {
    margin-bottom: 0;
    color: #d8dbd3;
    font-size: 17px;
}

.report-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-top: 1px solid var(--line-dark);
    border-left: 1px solid var(--line-dark);
}

.report-item {
    min-height: 230px;
    padding: 30px;
    border-right: 1px solid var(--line-dark);
    border-bottom: 1px solid var(--line-dark);
    background: var(--surface);
}

.report-item h3 {
    margin-bottom: 14px;
    font-size: 24px;
    line-height: 1.25;
}

.report-item p {
    margin-bottom: 0;
    color: var(--muted);
    font-size: 17px;
}

.quote {
    max-width: 900px;
    margin: 0;
    padding: 38px 0 38px 34px;
    border-left: 6px solid var(--accent);
}

.quote p {
    margin-bottom: 20px;
    font-size: clamp(28px, 4vw, 42px);
    line-height: 1.25;
    letter-spacing: -0.025em;
}

.quote footer {
    color: var(--muted);
    font-size: 17px;
}

.faq-list {
    border-top: 2px solid var(--ink);
}

.faq-item {
    display: grid;
    grid-template-columns: minmax(250px, 0.8fr) minmax(0, 1.2fr);
    gap: 44px;
    padding: 28px 0;
    border-bottom: 1px solid var(--line-dark);
}

.faq-item h3 {
    margin-bottom: 0;
    font-size: 21px;
    line-height: 1.35;
}

.faq-item p {
    margin-bottom: 0;
    color: var(--muted);
    font-size: 17px;
}

.contact-section {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 40px;
    align-items: end;
}

.contact-section h2 {
    max-width: 760px;
    margin-bottom: 20px;
    font-size: clamp(42px, 6vw, 70px);
    line-height: 1;
    letter-spacing: -0.05em;
}

.contact-section p {
    max-width: 700px;
    margin-bottom: 0;
    color: var(--muted);
    font-size: 20px;
}

.contact-actions {
    display: flex;
    flex-direction: column;
    gap: 12px;
    min-width: 230px;
}

.contact-email {
    color: var(--ink);
    font-size: 17px;
    font-weight: 700;
    text-align: center;
}

.site-footer {
    border-top: 1px solid var(--line-dark);
    background: var(--surface);
}

.footer-inner {
    width: min(1120px, calc(100% - 40px));
    min-height: 90px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 28px;
    font-size: 16px;
}

.footer-links {
    display: flex;
    flex-wrap: wrap;
    gap: 22px;
}

.footer-links a {
    font-weight: 700;
    text-decoration: none;
}

.footer-links a:hover {
    text-decoration: underline;
    text-underline-offset: 4px;
}

@media (max-width: 900px) {
    .nav-links a:not(.nav-action) {
        display: none;
    }

    .hero {
        grid-template-columns: 1fr;
        gap: 42px;
    }

    .metric-row,
    .process-grid,
    .report-grid {
        grid-template-columns: 1fr 1fr;
    }

    .metric:nth-child(2) {
        border-right: 0;
    }

    .metric:nth-child(3) {
        grid-column: 1 / -1;
        border-top: 1px solid var(--line);
    }

    .contact-section {
        grid-template-columns: 1fr;
        align-items: start;
    }

    .contact-actions {
        width: min(100%, 300px);
    }
}

@media (max-width: 640px) {
    .nav-inner,
    .page-section,
    .footer-inner {
        width: min(100% - 28px, 1120px);
    }

    .nav-inner {
        min-height: 68px;
    }

    .brand {
        font-size: 22px;
    }

    .nav-action {
        padding: 8px 12px;
        font-size: 15px;
    }

    .page-section,
    .dark-section .page-section {
        padding-top: 64px;
        padding-bottom: 64px;
    }

    .hero {
        padding-top: 64px;
        padding-bottom: 64px;
    }

    .hero h1 {
        font-size: 49px;
    }

    .hero p,
    .section-heading p,
    .contact-section p {
        font-size: 18px;
    }

    .button {
        width: 100%;
    }

    .metric-row,
    .flat-grid,
    .process-grid,
    .report-grid {
        grid-template-columns: 1fr;
    }

    .metric,
    .metric:nth-child(2),
    .metric:nth-child(3) {
        grid-column: auto;
        border-right: 0;
        border-top: 1px solid var(--line);
    }

    .metric:first-child {
        border-top: 0;
    }

    .flat-card,
    .process-step,
    .report-item {
        min-height: 0;
        padding: 26px;
    }

    .faq-item {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .footer-inner {
        padding: 24px 0;
        align-items: flex-start;
        flex-direction: column;
    }
}
</style>
"""


LANDING_HTML = """
<div class="seo-landing">
    <nav class="site-nav" aria-label="Main navigation">
        <div class="nav-inner">
            <a class="brand" href="#top"><span class="brand-mark" aria-hidden="true"></span>seotrophy</a>
            <div class="nav-links">
                <a href="#product">Product</a>
                <a href="#how-it-works">How it works</a>
                <a href="#report">Report</a>
                <a href="#faq">FAQ</a>
                <a href="#contact">Contact</a>
                <a class="nav-action" href="__PRIMARY_HREF__">__PRIMARY_LABEL__</a>
            </div>
        </div>
    </nav>

    <main>
        <section class="page-section hero" id="top">
            <div>
                <h1>SEO audits that tell you what to fix first.</h1>
                <p>Seotrophy crawls your website, reviews the page across four practical SEO layers, and turns the findings into a clear action plan.</p>
                <div class="hero-actions">
                    <a class="button" href="__PRIMARY_HREF__">__PRIMARY_LABEL__</a>
                    <a class="button button-secondary" href="#product">View the checks</a>
                </div>
            </div>

            <aside class="audit-example" aria-label="Example audit summary">
                <div class="audit-example-head">
                    <h2>Example audit</h2>
                    <span class="audit-score">88/100</span>
                </div>
                <ul class="audit-list">
                    <li><span>Technical SEO</span><strong>91</strong></li>
                    <li><span>Content quality</span><strong>84</strong></li>
                    <li><span>Trust and usability</span><strong>87</strong></li>
                    <li><span>Prioritized actions</span><strong>18 fixes</strong></li>
                </ul>
            </aside>
        </section>

        <section class="metric-row" aria-label="Product metrics">
            <div class="metric"><strong>140+</strong><span>SEO signals reviewed in each audit</span></div>
            <div class="metric"><strong>4</strong><span>intelligence layers combined into one report</span></div>
            <div class="metric"><strong>&lt; 60s</strong><span>typical time to receive the first report</span></div>
        </section>

        <section class="page-section" id="product">
            <div class="section-heading">
                <h2>One audit. Four useful layers.</h2>
                <p>Each layer answers a different question, then contributes to one practical SEO score and one ranked list of fixes.</p>
            </div>

            <div class="flat-grid">
                <article class="flat-card">
                    <div class="score-line"><h3>Technical</h3><strong>91</strong></div>
                    <p>Checks crawlability, indexability, canonical tags, status codes, redirects, structured data, and technical page health.</p>
                </article>
                <article class="flat-card">
                    <div class="score-line"><h3>Content</h3><strong>84</strong></div>
                    <p>Reviews search intent, topic coverage, titles, descriptions, headings, readability, and the depth of the page.</p>
                </article>
                <article class="flat-card">
                    <div class="score-line"><h3>Trust and usability</h3><strong>87</strong></div>
                    <p>Finds weak trust signals, accessibility problems, mobile friction, unclear calls to action, and layout issues.</p>
                </article>
                <article class="flat-card">
                    <div class="score-line"><h3>Action plan</h3><strong>Ranked</strong></div>
                    <p>Turns every finding into a clear next step, ordered by likely impact so the most important work comes first.</p>
                </article>
            </div>
        </section>

        <section class="dark-section" id="how-it-works">
            <div class="page-section">
                <div class="section-heading">
                    <h2>From page to action plan.</h2>
                    <p>The process is fixed, transparent, and designed to produce a report that can be used immediately.</p>
                </div>

                <div class="process-grid">
                    <article class="process-step">
                        <span class="process-number">01</span>
                        <h3>Submit</h3>
                        <p>Choose the page or website you want Seotrophy to review.</p>
                    </article>
                    <article class="process-step">
                        <span class="process-number">02</span>
                        <h3>Crawl</h3>
                        <p>Seotrophy collects the page structure, metadata, content, links, and technical signals.</p>
                    </article>
                    <article class="process-step">
                        <span class="process-number">03</span>
                        <h3>Inspect</h3>
                        <p>The page is checked for technical, content, trust, accessibility, and usability issues.</p>
                    </article>
                    <article class="process-step">
                        <span class="process-number">04</span>
                        <h3>Score</h3>
                        <p>The findings are weighted and combined into readable layer scores.</p>
                    </article>
                    <article class="process-step">
                        <span class="process-number">05</span>
                        <h3>Explain</h3>
                        <p>Each issue is described in plain language with enough context to understand why it matters.</p>
                    </article>
                    <article class="process-step">
                        <span class="process-number">06</span>
                        <h3>Prioritize</h3>
                        <p>The final report ranks the work so you know exactly where to start.</p>
                    </article>
                </div>
            </div>
        </section>

        <section class="page-section" id="report">
            <div class="section-heading">
                <h2>A report built for action.</h2>
                <p>No animated dashboard and no decorative charts. The report focuses on the information needed to improve the website.</p>
            </div>

            <div class="report-grid">
                <article class="report-item">
                    <h3>Crawl and index review</h3>
                    <p>See indexability, status codes, redirects, canonical relationships, and crawl problems together.</p>
                </article>
                <article class="report-item">
                    <h3>Structured data review</h3>
                    <p>Find missing or malformed schema and understand where structured data should be added.</p>
                </article>
                <article class="report-item">
                    <h3>Search intent review</h3>
                    <p>Identify sections that do not match the likely purpose of the query or the expectations of visitors.</p>
                </article>
                <article class="report-item">
                    <h3>Page X-Ray</h3>
                    <p>Review the visible page structure and find layout problems that ordinary source checks can miss.</p>
                </article>
                <article class="report-item">
                    <h3>Trust and accessibility</h3>
                    <p>Check alternative text, contrast, mobile tap targets, credibility signals, and visitor friction.</p>
                </article>
                <article class="report-item">
                    <h3>Saved and exportable reports</h3>
                    <p>Keep completed audits in your history and share the findings with teammates or clients.</p>
                </article>
            </div>
        </section>

        <section class="page-section section-border">
            <blockquote class="quote">
                <p>“We stopped guessing which page to fix first. The ranked action list made the next steps obvious.”</p>
                <footer>Marta L., Head of Growth</footer>
            </blockquote>
        </section>

        <section class="page-section section-border" id="faq">
            <div class="section-heading">
                <h2>Frequently asked questions.</h2>
                <p>Clear answers before you run the first audit.</p>
            </div>

            <div class="faq-list">
                <article class="faq-item">
                    <h3>Is the report only AI-generated text?</h3>
                    <p>No. The process begins with a real crawl of the page. AI explains and prioritizes the collected findings rather than inventing them.</p>
                </article>
                <article class="faq-item">
                    <h3>Does every audit use credits?</h3>
                    <p>Yes. Each run crawls the website, processes the collected signals, and creates a new structured report.</p>
                </article>
                <article class="faq-item">
                    <h3>Which website types are supported?</h3>
                    <p>Seotrophy can review SaaS websites, local businesses, e-commerce stores, portfolios, publications, and other public websites.</p>
                </article>
                <article class="faq-item">
                    <h3>Does it replace an SEO expert?</h3>
                    <p>No. It reduces the time spent finding and organizing issues, leaving the final strategy and implementation decisions to you or your team.</p>
                </article>
                <article class="faq-item">
                    <h3>What is Page X-Ray?</h3>
                    <p>Page X-Ray examines the visible structure of a page and highlights layout or section-level problems that source data alone may not reveal.</p>
                </article>
                <article class="faq-item">
                    <h3>Can reports be exported?</h3>
                    <p>Yes. Completed audits are saved to history and can be exported for clients, teammates, or later reference.</p>
                </article>
            </div>
        </section>

        <section class="page-section section-border contact-section" id="contact">
            <div>
                <h2>Start with one clear audit.</h2>
                <p>Run an audit, review the ranked findings, and focus on the work most likely to improve the website.</p>
            </div>
            <div class="contact-actions">
                <a class="button" href="__PRIMARY_HREF__">__PRIMARY_LABEL__</a>
                <a class="contact-email" href="mailto:hello@seotrophy.ai">hello@seotrophy.ai</a>
            </div>
        </section>
    </main>

    <footer class="site-footer">
        <div class="footer-inner">
            <span>© 2026 Seotrophy Inc.</span>
            <div class="footer-links">
                <a href="#product">Product</a>
                <a href="#how-it-works">How it works</a>
                <a href="#report">Report</a>
                <a href="#faq">FAQ</a>
                <a href="#contact">Contact</a>
            </div>
        </div>
    </footer>
</div>
"""


def _render_landing_html(primary_href: str, primary_label: str) -> str:
    """Build the static landing page with the correct account action."""
    html = LANDING_HTML
    html = html.replace("__PRIMARY_HREF__", primary_href)
    html = html.replace("__PRIMARY_LABEL__", primary_label)
    return html


def landingView() -> None:
    """Render the static Seotrophy landing page."""
    logged_in = bool(st.session_state.get("uid"))

    primary_href = "/new" if logged_in else "/login"
    primary_label = "Start audit" if logged_in else "Run a free audit"

    page_html = (
        LANDING_CSS
        + _render_landing_html(
            primary_href=primary_href,
            primary_label=primary_label,
        )
    )

    st.html(page_html)

