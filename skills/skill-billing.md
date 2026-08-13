---
name: billing
description: Generate and send invoices from time tracking data
triggers:
  - invoice
  - billing
  - bill
---

# Billing Skill

Canonical billing workflow lives in `billing/billing-skill.md`.

## Quick Reference

**Generate invoice only:**
```bash
python3 billing/generate_invoice.py <ClientName> <Month> [Year]
```

**Generate and send for review:**
```bash
python3 billing/generate_invoice.py <ClientName> <Month> [Year] --send
```

**Generate and send directly to client:**
```bash
python3 billing/generate_invoice.py <ClientName> <Month> [Year] --send --direct
```

**Update sheet after invoicing:**
```bash
python3 billing/finalize_invoice.py <ClientName> <Month>
```

## Rules
- Run `finalize_invoice.py` immediately after generating.
- Do not send the same invoice number twice.
- Client details, rates, and email config live in `billing/clients.yaml` (gitignored).

## Full Docs
See `billing/billing-skill.md` for the canonical workflow, email format, and signature rules.
