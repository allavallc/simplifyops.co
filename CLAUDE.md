# CLAUDE.md - SimplifyOps.co

## WORKING STYLE (READ FIRST)

### Permanent Fixes Over Quick Fixes
- **Always distinguish** between a temporary/quick fix and a permanent fix
- If proposing a quick fix, explicitly say "This is a temporary fix" and explain the permanent alternative
- Default to permanent fixes (config files, environment variables, docker-compose.yml) over runtime commands that get wiped on restart

### Minimal Code
- Write the **minimum code required** to solve the problem
- Prefer configuration (TypeScript config, markdown, YAML, environment variables) over custom code
- Do not create helpers, utilities, or abstractions unless absolutely necessary
- If a framework or tool provides a built-in solution, use it instead of writing custom code

### Explain Before Acting
- **Always tell the user what you're going to do BEFORE doing it**
- Explain what each command does and why
- For non-trivial changes, ask "Want me to proceed?"
- Never run commands silently or make changes without explanation

---

## SECURITY RULES

This is a **PUBLIC repository**. The following rules are non-negotiable:

### Never Include:
- Personal information (full name, address, phone number, email addresses)
- API keys, tokens, or credentials of any kind
- Private repository references or paths
- Client names, project details, or confidential business information
- Internal URLs or infrastructure details
- Anything from the private `00_coo_brain` knowledge base directly

### Contact Form Security:
- The only contact method is a form that sends email server-side
- **Never expose email addresses in HTML, JavaScript, or any client-side code**
- Use a privacy-respecting form backend (Formspree, Netlify Forms, or similar)
- The form backend handles email delivery - the actual email address stays hidden
- Include honeypot fields and/or rate limiting to prevent spam

### Content Guidelines:
- Blog posts may reference general experience and methodologies
- Use anonymized examples only (no real client names or identifiable details)
- Metrics and results should be generalized ("a client" not "Company X")

---

## Project Overview

Automated SEO blog engine for simplifyops.co:
- Weekly blog generation via Hermes Agent
- Telegram approval workflow before publishing
- GitHub Pages hosting (auto-deploys on push)
- Billing automation for client invoicing (Google Sheets → PDF → Gmail)

## Repository Structure

```
simplifyops.co/
├── index.html                  # Landing page
├── blog/
│   ├── index.html              # Blog listing
│   └── posts/                  # Individual posts (YYYY-MM-DD-title.md)
├── contact/
│   └── index.html              # Contact form (NO exposed email)
├── assets/css/
├── billing/
│   ├── generate_invoice.py     # Reads Sheet → generates PDF → sends email
│   ├── finalize_invoice.py     # Marks sheet rows Invoiced=Yes + Invoice #
│   ├── invoice-template.html   # Jinja2 HTML template for PDF
│   ├── billing-skill.md        # Full billing workflow docs
│   ├── clients-example.yaml    # Public example config (committed)
│   └── clients.yaml            # GITIGNORED — all secrets live here
├── skills/
│   └── skill-billing.md        # Quick-ref skill pointing to billing/
├── souls/
│   └── james-bott.md           # CEO persona definition
├── invoices/                   # GITIGNORED — generated PDFs
└── graphify-out/               # GITIGNORED — knowledge graph outputs
```

## Billing System

### Gitignore rules (enforced — never override)
- `billing/clients.yaml` — SMTP password, emails, addresses, phone, Sheet ID, service account path
- `billing/sent_log.json` — duplicate send log (never delete)
- `invoices/` — generated PDFs

### Workflow (in order — never skip finalize)
```powershell
# 1. Generate invoice (PDF saved to invoices/)
python billing/generate_invoice.py <ClientName> <Month> [Year]

# 2. Generate + send to business email for review
python billing/generate_invoice.py <ClientName> <Month> [Year] --send

# 3. Generate + send directly to client
python billing/generate_invoice.py <ClientName> <Month> [Year] --send --direct

# 4. MANDATORY — mark sheet rows Invoiced=Yes and stamp Invoice #
python billing/finalize_invoice.py <ClientName> <Month>
```

**Always run `finalize_invoice.py` immediately after generating.** If skipped, the same hours reappear in next month's invoice.

### clients.yaml structure (gitignored)
All client config (sheet tab, email, rate), SMTP credentials, business info, payment options, and signature (`agent_name`, `owner_name`, `company`) live in `billing/clients.yaml`. Never hardcode any of this in scripts — always read from config.

### Email format
- Casual but professional; no hours, rate, total, or payment details in body
- Signature: `agent_name` / `On behalf of owner_name | company` (from `clients.yaml signature` section)
- `--send` → business email (for review); `--send --direct` → client email
- Duplicate send protection via `billing/sent_log.json` — script refuses to re-send same invoice number

### Service account key (WSL path)
`/home/adefilippo/.config/gcloud/simplifyops-co-1cf850b44c9a.json`

## Contact Form Implementation

Use one of these privacy-safe approaches:

**Option 1: Formspree (recommended for simplicity)**
```html
<form action="https://formspree.io/f/{form_id}" method="POST">
  <!-- honeypot field for spam prevention -->
  <input type="text" name="_gotcha" style="display:none">
  <input type="text" name="name" required>
  <input type="email" name="email" required>
  <textarea name="message" required></textarea>
  <button type="submit">Send</button>
</form>
```

**Option 2: Netlify Forms (if hosting on Netlify)**
```html
<form name="contact" method="POST" data-netlify="true" netlify-honeypot="bot-field">
  <input type="hidden" name="bot-field">
  <!-- form fields -->
</form>
```

The form_id/configuration lives in the external service, not in this repo.

## Tech Stack

- Static site: HTML/CSS (Jekyll optional)
- Hosting: GitHub Pages
- Contact: Formspree or equivalent
- Content generation: Hermes Agent + Claude API
- Web search: ddgs (DuckDuckGo CLI)

## Project Configuration

- `.hermes.md` — Project-specific paths, rules, and settings
- `souls/` — Agent personas (James Bott)
- `_posts/` — Blog posts (Jekyll format)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
