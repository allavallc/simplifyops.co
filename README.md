# SimplifyOps.co

Automated SEO blog engine for simplifyops.co using Hermes Agent + Paperclip.

## Quick Start

1. Start Docker Desktop (disconnect VPN first)
2. Open WSL
3. Run:
   ```bash
   cd ~/paperclip-wsl/paperclip-source && docker compose up -d
   ```

This starts:
- **Hermes CEO** — Telegram bot for content approval
- **Paperclip** — Dashboard at http://localhost:3100
- **Postgres** — Database on port 5433

To stop:
```bash
cd ~/paperclip-wsl/paperclip-source && docker compose down
```

## Workflow

1. Start the stack (see above)
2. Message the CEO on Telegram
3. Review drafts, approve or give feedback
4. CEO commits and pushes to GitHub
5. GitHub Pages auto-deploys

## Architecture

```
simplifyOps.co/          # Website (GitHub Pages)
├── index.html           # Landing page
├── _posts/              # Blog posts (Jekyll)
├── billing/             # Invoice generation
└── contact/             # Contact form
```
