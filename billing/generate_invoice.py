#!/usr/bin/env python3
"""
Invoice Generator — reads Google Sheet, generates PDF, sends email.
Controlled by clients.yaml and invoice-template.md
"""

import sys
import json
import yaml
import gspread
import smtplib
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from google.oauth2.service_account import Credentials
from jinja2 import Template

# For PDF generation
try:
    from weasyprint import HTML, CSS
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False

BILLING_DIR = Path(__file__).parent
CONFIG_FILE = BILLING_DIR / "clients.yaml"
TEMPLATE_FILE = BILLING_DIR / "invoice-template.html"
SENT_LOG = BILLING_DIR / "sent_log.json"


def load_sent_log():
    if SENT_LOG.exists():
        with open(SENT_LOG) as f:
            return json.load(f)
    return {}


def was_already_sent(invoice_number):
    return invoice_number in load_sent_log()


def record_sent(invoice_number, recipient):
    log = load_sent_log()
    log[invoice_number] = {"sent_at": datetime.now().isoformat(), "recipient": recipient}
    with open(SENT_LOG, "w") as f:
        json.dump(log, f, indent=2)


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def get_sheet_data(config, client_name):
    """Read hours from Google Sheet for a specific client."""
    client_config = config["clients"].get(client_name)
    if not client_config:
        raise ValueError(f"Client '{client_name}' not found in clients.yaml")

    creds = Credentials.from_service_account_file(
        config["service_account_key"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(config["google_sheet_id"])
    ws = sheet.worksheet(client_config["sheet_tab"])

    return ws.get_all_values(), client_config


def filter_entries(rows, month):
    """Filter rows for a specific month that haven't been invoiced."""
    entries = []

    # Find header row (contains 'Month', 'Date', etc.)
    header_idx = None
    for i, row in enumerate(rows):
        if "Month" in row and "Date" in row:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("Could not find header row in sheet")

    headers = rows[header_idx]
    month_col = headers.index("Month")
    date_col = headers.index("Date")
    hours_col = headers.index("Hours")
    min_col = headers.index("Min")
    notes_col = headers.index("Notes")
    invoiced_col = headers.index("Invoiced")

    for row in rows[header_idx + 1:]:
        if len(row) > invoiced_col:
            row_month = row[month_col].strip().lower() if row[month_col] else ""
            invoiced = row[invoiced_col].strip().lower() if len(row) > invoiced_col else ""

            if row_month == month.lower() and invoiced != "yes":
                entries.append({
                    "date": row[date_col],
                    "hours": row[hours_col] or "0",
                    "minutes": row[min_col] or "0",
                    "notes": row[notes_col] if len(row) > notes_col else ""
                })

    return entries


def calculate_total(entries, rate):
    """Calculate total hours and amount due."""
    total_minutes = 0
    for entry in entries:
        hours = int(entry["hours"]) if entry["hours"] else 0
        minutes = int(entry["minutes"]) if entry["minutes"] else 0
        total_minutes += hours * 60 + minutes

    total_hours = total_minutes / 60
    amount_due = total_hours * rate
    return total_hours, amount_due


def generate_invoice_html(config, client_name, month, year, entries, total_hours, amount_due):
    """Generate invoice HTML from template."""
    with open(TEMPLATE_FILE) as f:
        template = Template(f.read())

    client_config = config["clients"][client_name]

    return template.render(
        business=config["business"],
        payment=config.get("payment", {}),
        client={"name": client_name, "contact_name": client_config["contact_name"]},
        invoice_date=datetime.now().strftime("%B %d, %Y"),
        invoice_number=f"INV-{datetime.now().strftime('%Y%m%d')}-{client_name[:3].upper()}",
        month=month.capitalize(),
        year=year,
        entries=entries,
        total_hours=f"{total_hours:.2f}",
        rate=client_config["rate"],
        amount_due=f"{amount_due:,.2f}"
    )


def html_to_pdf(html_content, output_path):
    """Convert HTML to PDF."""
    if not HAS_WEASYPRINT:
        print("WARNING: weasyprint not installed. Saving as .html instead.")
        html_path = output_path.replace(".pdf", ".html")
        with open(html_path, "w") as f:
            f.write(html_content)
        return html_path

    HTML(string=html_content).write_pdf(output_path)
    return output_path


def build_email_body(client_name, month, year, signature):
    agent = signature.get("agent_name", "")
    owner = signature.get("owner_name", "")
    company = signature.get("company", "")
    return f"""Hey {client_name},

Hope you're doing well! Attached is your invoice for {month} {year} — let me know if anything looks off.

Thanks,
{agent}
On behalf of {owner} | {company}"""


def send_email(config, to_email, subject, body, attachment_path, filename=None):
    """Send invoice via email."""
    smtp_config = config["smtp"]

    msg = MIMEMultipart()
    msg["From"] = smtp_config["from_name"] + " <" + smtp_config["username"] + ">"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    attachment_name = filename or Path(attachment_path).name
    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
        msg.attach(part)

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.starttls()
        server.login(smtp_config["username"], smtp_config["password"])
        server.send_message(msg)

    print(f"Email sent to {to_email}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_invoice.py <ClientName> <Month> [Year] [--send]")
        print("Example: python generate_invoice.py ManagePro March 2026 --send")
        sys.exit(1)

    client_name = sys.argv[1]
    month = sys.argv[2]
    # Year is optional - defaults to current year
    year = None
    for arg in sys.argv[3:]:
        if arg.isdigit() and len(arg) == 4:
            year = int(arg)
            break
    if year is None:
        year = datetime.now().year
    send = "--send" in sys.argv

    config = load_config()

    # Get data
    print(f"Reading hours for {client_name} - {month}...")
    rows, client_config = get_sheet_data(config, client_name)
    entries = filter_entries(rows, month)

    if not entries:
        print(f"No uninvoiced entries found for {month}")
        sys.exit(0)

    print(f"Found {len(entries)} entries")

    # Calculate
    total_hours, amount_due = calculate_total(entries, client_config["rate"])
    print(f"Total: {total_hours:.2f} hours = ${amount_due:,.2f}")

    # Generate invoice number
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{client_name[:3].upper()}"

    # Generate invoice
    html_content = generate_invoice_html(config, client_name, month, year, entries, total_hours, amount_due)

    # Save PDF with filename: invoice-CLIENT-MONTH-INVOICE#
    invoices_dir = BILLING_DIR.parent / "invoices"
    invoices_dir.mkdir(exist_ok=True)
    output_path = invoices_dir / f"invoice-{client_name}-{month}-{invoice_number}.pdf"
    result_path = html_to_pdf(html_content, str(output_path))
    print(f"Invoice saved: {result_path}")
    print(f"Invoice number: {invoice_number}")

    # Send email if requested
    if send:
        direct = "--direct" in sys.argv
        to_email = client_config.get("contact_email") if direct else config["business"].get("email")

        if not to_email:
            print("ERROR: No recipient email configured")
            sys.exit(1)

        if was_already_sent(invoice_number):
            entry = load_sent_log()[invoice_number]
            print(f"ERROR: Invoice {invoice_number} was already sent to {entry['recipient']} at {entry['sent_at']}")
            print("Stopping to avoid duplicate. Use --force to override.")
            sys.exit(1)

        subject = f"Invoice for {month.capitalize()} {year} — SimplifyOps"
        body = build_email_body(client_config["contact_name"], month.capitalize(), year, config.get("signature", {}))
        filename = f"invoice-{client_name}-{month.capitalize()}-{year}.pdf"

        send_email(config, to_email, subject, body, result_path, filename=filename)
        record_sent(invoice_number, to_email)

    print("Done!")


if __name__ == "__main__":
    main()
