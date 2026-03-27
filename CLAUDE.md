# CLAUDE.md - SimplifyOps.co

## SECURITY RULES (READ FIRST)

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

## Repository Structure

```
simplifyops-site/
├── index.html              # Landing page
├── blog/
│   ├── index.html          # Blog listing
│   └── posts/              # Individual posts (YYYY-MM-DD-title.md)
├── contact/
│   └── index.html          # Contact form (NO exposed email)
└── assets/
    └── css/
```

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
- Content generation: Hermes Agent + Ollama (runs separately, not in this repo)
- Orchestration: Paperclip (optional, for multi-agent workflows)

## Local Development Setup

See `plan-architecture/starting-up.md` for step-by-step startup instructions.

**Quick start:**
1. Ollama: auto-starts (check system tray)
2. Hermes: `hermes chat --model hermes3:3b`
3. Paperclip: `npx paperclipai run` (requires admin PowerShell)
