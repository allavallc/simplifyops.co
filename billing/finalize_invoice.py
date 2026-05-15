import gspread
from google.oauth2.service_account import Credentials
import sys
import yaml
from pathlib import Path
from datetime import datetime

if len(sys.argv) < 3:
    print("Usage: python3 finalize_invoice.py <ClientName> <Month>")
    sys.exit(1)

client_name = sys.argv[1]
month_name = sys.argv[2]

BILLING_DIR = Path(__file__).parent
with open(BILLING_DIR / 'clients.yaml') as f:
    config = yaml.safe_load(f)

client_config = config['clients'].get(client_name)
if not client_config:
    print(f"Unknown client: {client_name}")
    print(f"Available clients: {', '.join(config['clients'].keys())}")
    sys.exit(1)

today = datetime.now().strftime('%Y%m%d')
invoice_number = f"INV-{today}-{client_name[:3].upper()}"

creds = Credentials.from_service_account_file(
    config['service_account_key'],
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(config['google_sheet_id'])
ws = sheet.worksheet(client_config['sheet_tab'])

all_data = ws.get_all_values()

# Find header row
header_idx = next((i for i, row in enumerate(all_data) if 'Month' in row and 'Invoiced' in row), None)
if header_idx is None:
    print("Error: Could not find header row")
    sys.exit(1)

header = all_data[header_idx]
invoiced_col_idx = header.index('Invoiced')
invoice_num_col_idx = header.index('Invoice #') if 'Invoice #' in header else None

if invoice_num_col_idx is None:
    print("Error: Could not find 'Invoice #' column")
    sys.exit(1)

month_col_idx = header.index('Month')

target_rows = []
for idx, row in enumerate(all_data[header_idx + 1:], start=header_idx + 2):
    month_val = row[month_col_idx] if len(row) > month_col_idx else ''
    if month_val == month_name:
        target_rows.append(idx)

if target_rows:
    for row_idx in target_rows:
        ws.update_cell(row_idx, invoiced_col_idx + 1, 'Yes')
        ws.update_cell(row_idx, invoice_num_col_idx + 1, invoice_number)
    print(f'Updated {len(target_rows)} {month_name} rows:')
    print(f'  Invoiced: Yes | Invoice #: {invoice_number}')
else:
    print(f'No {month_name} rows found for {client_name}')
