# CLAUDE.md - SimplifyOps.co

## WORKING STYLE (READ FIRST)

### Read the Graph Report First
- **Before coding, bugfixing, or proposing architecture changes:** run `graphify update .` and read `graphify-out/GRAPH_REPORT.md`
- The graph is the primary map of the codebase — use it before reading raw files or running grep searches
- After modifying code, run `graphify update .` to keep it current

### No Architecture Choices Without Asking
- **Never make an architecture decision unilaterally** — this includes implementation approach, service boundaries, data model shape, technology selection, and anything that affects long-term system design
- If there is more than one reasonable way to implement something, stop and ask before choosing
- "Simplest path" is not a reason to pick an approach — ask what the right shape is

### No Short-Term Fixes
- **Never implement a workaround "just to get something working"** — if the right architecture requires more work, do it right or don't do it yet
- If something can't be done properly right now, say so explicitly and explain what the proper approach requires
- Temporary scaffolding that will need to be ripped out later is not acceptable — it creates debt and bad behavior that is harder to debug than no implementation at all

### Minimal Code
- Write the **minimum code required** to solve the problem
- Prefer configuration (TypeScript config, markdown, YAML, environment variables) over custom code
- Do not create helpers, utilities, or abstractions unless absolutely necessary
- If a framework or tool provides a built-in solution, use it instead of writing custom code

### James is off-limits

**Never send messages to James directly.** Do not call `POST /messages` or any admin API endpoint to inject messages, do not message the Telegram bot, and do not simulate user messages via any API or script. All interaction with James goes through the owner. Injecting messages — even for testing — burns through session limits, corrupts task context, and produces confusing replies mid-task.

### Stories First
- **All work requires a story in `product/stories/` before implementation starts**
- Each story file must have a number in the title: `story-N-<title>.md`
- Write the story, present the plan, wait for approval before coding
- Stories are permanent — do not reuse numbers
- **Lifecycle:** story → plan → approval → branch → **code → write logging → write tests → commit (WIP)** → **rebase onto `origin/main`** → **`brooks-review` + `brooks-audit` → fix, re-run until clean** → **focused `ruff` + `pytest`** → **full `ruff` + `pytest`** → **amend → push** → merge to `main` → archive story → delete branch
- **Rebase before the gate — never skip:** commit WIP, then `git fetch origin && git rebase origin/main`, **then** run the gate on the rebased result — so your checks validate the *integrated* code and "green" can't be stale (the merge can't silently reverse someone else's work). Resolve conflicts before running the gate.
- **Mandatory review gate:** run **both** `brooks-review` (diff) **and** `brooks-audit` (architecture) — the brooks-lint skills in `.agents/skills/` — **on the rebased branch (after commit + rebase, before push/merge).** Reviews are static (read code + tests, don't run them); iterate until clean, **then** run focused + full `ruff`/`pytest`. An unresolved 🔴 **Critical** from **either** **blocks push/merge** — fix it or record an explicit justification in the story's Review section. See `AGENTS.md` rule 9.
- **Testing-phase readout:** during the testing phase, print and keep updating a status line marking the current stage with `(**HERE**)`, e.g. `brooks audit > fixing findings > focused ruff > focused pytest (**HERE**) > full ruff > full pytest > done`.

### Explain Before Acting
- **Always tell the user what you're going to do BEFORE doing it**
- Explain what each command does and why
- For non-trivial changes, ask "Want me to proceed?"
- Never run commands silently or make changes without explanation

### MCP Work
- MCP server/connector changes are **architecture decisions** — plan and get owner approval first (per "No Architecture Choices Without Asking"), like any other boundary change. No special external sign-off is required.
- The third-party `@dguido/google-workspace-mcp` self-manages OAuth and bypasses app governance/audit — this conflicts with the repo-owned MCP model. Prefer repo-owned connectors.

---

## CURRENT SYSTEM STATE (2026-08-11)

James (Hermes agent) is **functional** — `gpt-5.5` via `openai-codex`, profile `simplifyops`.

### Services (all active, systemd)
| Service | Purpose | Port |
|---|---|---|
| `simplifyops-admin.service` | FastAPI control plane: `POST /messages`, admin UI, governance, audit, settings | 3000 |
| `simplifyops-gateway.service` | Telegram adapter + DurableWorkflowWorker | 3001 (internal) |
| `simplifyops-agent-runtime.service` | Hermes gateway run + API server | 8642 |
| `hindsight.service` | Memory (Hindsight) | 8888 |

_(The legacy `people-whitelist.service` Node app was removed — governance is owned by `admin_api/`.)_

### Message flow
Telegram → `gateway/gateway.py` adapter → `POST http://127.0.0.1:3000/messages` → governance (`person_identities`→`people`) → `work_items(ready)` → DurableWorkflowWorker (concurrency=1) → session-cap check/rotate → `POST http://127.0.0.1:8642/api/sessions/{id}/chat` → `reply_ready` → Telegram send → `completed`. Runtime/timeout failures retry ≤3 → `failed_needs_review` + Telegram alert.

### Where things live
- FastAPI control plane: `admin_api/` (main.py, routes/, templates/, static/, schema.sql)
- Durable worker + Telegram adapter: `gateway/gateway.py`; gateway tables: `gateway/sql/schema.sql`
- Hermes config (env-owned, gitignored): `/home/pi/.hermes/profiles/simplifyops/config.yaml`
- Secrets: `/home/pi/.config/relay.env` (admin+gateway), `/home/pi/.config/simplifyops-runtime.env` (runtime, root-owned)
- Canonical architecture: `product/product-decisions/current-architecture.md`. Stories: `product/stories/`.

### Database (`whitelist_app`, unix socket `/var/run/postgresql`)
`people` (+authority/can_converse/can_influence/status), `person_identities`, `requests`, `channel_events`, `work_items` (+payload jsonb), `hermes_session_mappings` (+logical_session_id/rotation_reason), `admin_settings` (session_message_cap default 100), `tool_contexts`, `contact_requests`, `audit_log`, `google_tokens`.

### Settings page (`/admin/settings`) — working backends
Health (Admin API/Soul/Memory URL/Postgres live status), Provider+Model (writes config.yaml → restart runtime → clear sessions), Session Health (cap → admin_settings). Other sections are UI-only.

### Standard fixes
```bash
sudo systemctl restart simplifyops-admin.service
sudo systemctl restart simplifyops-gateway.service
sudo systemctl restart simplifyops-agent-runtime.service   # API reconnects ~15s
# stuck 'processing' items after a crash:
psql "postgresql:///whitelist_app?host=/var/run/postgresql" -c "UPDATE work_items SET status='ready', locked_until=NULL WHERE status='processing' AND locked_until<now();"
```
NEVER delete/mask/disable service files.

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
├── gateway/
│   ├── gateway.py              # Channel-agnostic Telegram→Hermes bridge
│   ├── session_history.json    # GITIGNORED — per-user conversation history
│   └── whitelist/
│       └── (whitelist.md removed — governance now in people DB)
├── skills/
│   └── skill-billing.md        # Quick-ref skill pointing to billing/
├── souls/
│   └── soul.md           # CEO persona definition
├── ops/
│   └── persistent-mcp-setup.md # ATTEMPTED + FAILED — HTTP MCP transport docs
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

## Gateway (James ↔ Telegram)

- **Script:** `gateway/gateway.py` — systemd service `simplifyops-gateway.service`
- **Architecture:** channel-agnostic router; `handle_message()` is the central entry point
- **Telegram adapter:** long-polls Telegram, calls `handle_message()` per message
- **Internal HTTP server:** listens on `127.0.0.1:3001` at `/internal/reply` — receives approval callbacks from the FastAPI admin (`admin_api/`) after an admin approves an unknown sender
- **Governance:** `people` table in `whitelist_app` DB — `telegram_id`, `can_converse`, `authority`, `status`
- **Unknown senders:** queued to the FastAPI admin inbox (`contact_requests` via `admin_api/`); sender UX pending decision (currently no reply sent to unknown senders)
- **Session history:** last 25 exchanges per user in `gateway/session_history.json`; prepended to each Hermes prompt
- **Hermes call:** `hermes -p simplifyops -z "<history + message>"`

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
