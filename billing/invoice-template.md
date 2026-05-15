# INVOICE

**From:** {{ business.name }}
**Address:** {{ business.address }}
**Date:** {{ invoice_date }}
**Invoice #:** {{ invoice_number }}
**Bill Month:** {{ month }} {{ year }}

---

**Bill To:** {{ client.contact_name }}

---

## Services Rendered — {{ month }} {{ year }}

| Date | Hours | Description |
|------|-------|-------------|
{% for entry in entries %}| {{ entry.date }} | {{ entry.hours }}h {{ entry.minutes }}m | {{ entry.notes }} |
{% endfor %}

---

**Total Hours:** {{ total_hours }}
**Rate:** ${{ rate }}/hour

## Amount Due: ${{ amount_due }}

---

Payment due within 30 days.
Thank you for your business!
