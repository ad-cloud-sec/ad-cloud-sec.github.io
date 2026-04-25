When publishing a new post:
1. Create posts/[slug].html
2. Add post card to top of .post-list in index.html
3. Add entry to top of Writing section in README.md
4. git add, commit, push

---

## BEFORE WRITING A NEW POST — ASK THESE

1. Topic — Core thesis in one sentence.
2. Source material — Internal doc? What needs anonymising?
3. Audience — Practitioners? Architects? SOC analysts?
4. Count — If structured (controls, rules, findings), how many?
5. Kicker tags — 4-5 technical tags for the masthead.
6. Off-limits — Internal names, tool names, dates, org details.

---

## THEME

Fonts:
- Headings: Space Grotesk (wght 400;500;700)
- Body: Inter (wght 300;400;500;600)
- Mono/code: Fira Code (wght 400;500)

Google Fonts import:
https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Inter:wght@300;400;500;600&family=Fira+Code:wght@400;500&display=swap

Colors:
--ink:        #e8e2d9
--ink-light:  #a89f8c
--ink-muted:  #6b6457
--rule:       #1e2130
--code-bg:    #0c0e14
--code-border:#1e2130
--accent:     #38b2ac
--page:       #0f1117

Always include:
html, body { background: #0f1117 !important; color-scheme: dark; }

Typography:
- h1: Space Grotesk 700, clamp(26px,5vw,40px), letter-spacing -0.02em
- h2: Space Grotesk 700, 22px, letter-spacing -0.01em, border-bottom 1px var(--rule)
- h3: Fira Code 500, 11px, uppercase, letter-spacing 0.12em, color var(--ink-muted)
- body: Inter 300, 18px, line-height 1.75
- inline code: Fira Code 14px, background var(--code-bg), color var(--accent)
- code block: Fira Code 13px, border-left 3px solid var(--ink-muted)

Callout block:
.callout {
  border-left: 3px solid var(--accent);
  margin: 32px 0;
  padding: 16px 20px;
  background: #1a1d27;
}

Masthead:
.masthead {
  border-top: 3px solid var(--ink);
  border-bottom: 1px solid var(--rule);
  padding: 32px 0 28px;
  margin-bottom: 56px;
}

Max content width: 740px. Nav/footer max-width: 820px.

---

## HTML STRUCTURE (EVERY POST)

<nav class="site-nav" aria-label="Main navigation">
  <a href="/" class="logo">AD · Cloud Security</a>
  <a href="/" aria-label="Back to all posts">← All Posts</a>
</nav>

<main class="page">
<article>
<header class="masthead">
  <div class="kicker">Tag · Tag · Tag · Tag</div>
  <h1>Title</h1>
  <p class="deck">Deck paragraph</p>
</header>
<section>
  <!-- body content -->
</section>
</article>
</main>

<footer>
  <span>ad-cloud-sec.github.io</span>
  <a href="https://www.linkedin.com/in/amardip-deshpande/" target="_blank" rel="noopener noreferrer">LinkedIn →</a>
</footer>

---

## SEO BLOCK (REQUIRED IN EVERY POST)

<meta name="description" content="[150 chars max]">
<link rel="canonical" href="https://ad-cloud-sec.github.io/posts/[slug].html">
<meta property="og:title" content="[title]">
<meta property="og:description" content="[1-2 sentence summary]">
<meta property="og:type" content="article">
<meta property="og:url" content="https://ad-cloud-sec.github.io/posts/[slug].html">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="[title]">
<meta name="twitter:description" content="[summary]">
<meta name="twitter:label1" content="Reading time">
<meta name="twitter:data1" content="[N] minutes">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "[title]",
  "description": "[description]",
  "author": {"@type": "Person", "name": "Amardip Deshpande", "url": "https://ad-cloud-sec.github.io"},
  "datePublished": "[YYYY-MM-DD]",
  "dateModified": "[YYYY-MM-DD]",
  "publisher": {"@type": "Organization", "name": "AD Cloud Security", "url": "https://ad-cloud-sec.github.io"},
  "url": "https://ad-cloud-sec.github.io/posts/[slug].html",
  "keywords": ["keyword1", "keyword2"]
}
</script>

---

## INDEX.HTML POST CARD TEMPLATE

<a href="posts/[slug].html" class="post-item">
  <div class="post-date">Mon YYYY</div>
  <div class="post-content">
    <div class="post-category">Tag · Tag · Tag</div>
    <div class="post-title">[Full title]</div>
    <div class="post-excerpt">[2-3 sentence excerpt]</div>
    <span class="post-read">Read →</span>
  </div>
</a>

---

## README.MD ENTRY TEMPLATE

- [Title](https://ad-cloud-sec.github.io/posts/[slug].html) — [One sentence matching the deck]

---

## WRITING RULES

Voice:
- First-person practitioner: "I built this", "I found this during the assessment"
- Specific enterprise artifacts, not generalised theory
- Qualified uncertainty: "in most tenants", "by default", "in most deployments"
- Acknowledge what is hard, non-obvious, or breaks in real environments

Lead with the security argument, not the config step:
- BAD: "Set Assignment Required on the connector enterprise app."
- GOOD: "Until Assignment Required is set, any user in the tenant can authorise the integration with their full access. This is the active exposure window."

Structure:
- Deliberately uneven. Some sections 3 paragraphs, some 8. Symmetry signals AI.
- No bullet lists for prose. Lists only for genuinely enumerable items.
- Closing section must add something new. Never restate the opening argument.

Never include:
- Em dashes. Use a period and a new sentence instead.
- "Checklist" to describe a security controls document
- Tutorial language: "click here", "navigate to", "you should see"
- Words: "straightforward", "genuinely", "honestly"
- Operational instructions inside security-framing sections
- LLM patterns: symmetric structure, uniform paragraph length, binary contrasts, generic closings

Anonymisation:
- No company names
- No internal tool names (use category: MDM, CASB, SIEM, EDR)
- No internal dates, ticket numbers, artifact names
- No employee names or specific roles
- No internal org structure

---

## QUALITY CHECKLIST

- [ ] Zero em dashes in body text
- [ ] No Playfair Display, Source Serif 4, or JetBrains Mono in CSS
- [ ] No amber #c9933a in CSS
- [ ] No internal company or tool names
- [ ] No tutorial language in security sections
- [ ] Every h2 has an anchor id
- [ ] All target="_blank" links have rel="noopener noreferrer"
- [ ] th scope="col" on all table headers
- [ ] ARIA labels on nav and back link
- [ ] Semantic HTML: main, article, header, section, footer
- [ ] SEO meta block complete
- [ ] Closing section adds new insight
- [ ] Opening heading aligns with title thesis
- [ ] Word count 2,500-4,000 for deep-dive posts

---

## QUEUED POSTS

- Shadow AI detection
- How AI usage affects your data classification policy
- Claude and its connectors
- How to securely pilot Claude + M365 integration
