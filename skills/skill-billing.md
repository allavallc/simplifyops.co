---
name: billing
description: Generate and send invoices from time tracking data
triggers:
  - invoice
  - billing
  - bill
---

# Billing Skill

Handles invoicing for SimplifyOps. Full implementation lives in `billing/`.

## Quick Reference

**Generate invoice:**
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

**Update sheet after invoicing (mandatory):**
```bash
python3 billing/finalize_invoice.py <ClientName> <Month>
```

## Rules
- Always run `finalize_invoice.py` immediately after generating — marks rows as invoiced and stamps the invoice number. Skipping causes double-billing next month.
- Duplicate send protection is automatic — `invoices/sent_log.json` blocks re-sending the same invoice number.
- Client details, rates, and email config live in `billing/clients.yaml` (gitignored — not in repo).

## Full Docs
See `billing/billing-skill.md` for complete workflow, email format, and signature rules.
