---
name: billing
description: Generate and send invoices from time tracking data
triggers:
  - invoice
  - billing
  - bill
---

# Billing Agent Skill

Full billing workflow for SimplifyOps.

## Commands

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

Year defaults to current year. Pass explicitly when billing for a prior year (e.g., December billed in January).

## Workflow

1. Parse client name and month from the request
2. Determine the correct year:
   - If billing month is later in the calendar than the current month → use previous year
   - Otherwise use current year
3. Run `generate_invoice.py` — reports hours, amount, invoice number, PDF path
4. **Immediately** run `finalize_invoice.py` — do not skip (see below)
5. If sending, confirm duplicate check passed and email was sent

## Email Format

- Casual but professional tone
- Do NOT include hours, rate, total, or payment details — those are on the invoice
- Month in the email body must match the invoice attached
- Signature format (from `billing/clients.yaml` `signature` section):

```
Thanks,
[signature.agent_name]
On behalf of [signature.owner_name] | [signature.company]
```

## Duplicate Send Protection

`invoices/sent_log.json` tracks every sent invoice number. The script refuses to send the same invoice twice. Do not delete this file.

## Updating the Sheet — Mandatory

Run immediately after generating. Marks rows `Invoiced: Yes` and stamps the invoice number. If skipped, the same hours appear in next month's invoice.

## Config Files (gitignored — not in repo)
- `billing/clients.yaml` — client details, rates, emails, SMTP credentials
- `billing/sent_log.json` — duplicate send log

## Template & Scripts
- `billing/invoice-template.html` — PDF layout
- `billing/generate_invoice.py` — main script (reads sheet, generates PDF, sends email)
- `billing/finalize_invoice.py` — marks sheet rows as invoiced
