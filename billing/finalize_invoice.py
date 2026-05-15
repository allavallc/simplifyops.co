import gspread
from google.oauth2.service_account import Credentials
import sys
import yaml
from datetime import datetime

# Get client name and month from args
if len(sys.argv) < 3:
    print("Usage: python3 finalize_invoice.py <ClientName> <Month>")
    sys.exit(1)

client_name = sys.argv[1]
month_name = sys.argv[2]

# Load config
with open('billing/clients.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Generate invoice number with today's date
today = datetime.now().strftime('%Y%m%d')
invoice_number = f"INV-{today}-{client_name[:3].upper()}"

# Connect to Google Sheets
creds = Credentials.from_service_account_file(
    config['service_account_key'],
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(config['google_sheet_id'])

# Determine sheet tab name
if client_name == 'ManagePro':
    tab_name = 'Nate - ManagePro'
else:
    print(f"Unknown client: {client_name}")
    sys.exit(1)

ws = sheet.worksheet(tab_name)

# Get all data - header is on row 3 (index 2)
all_data = ws.get_all_values()
header = all_data[2]  # Row 3 is the header

# Find column indices
invoiced_col_idx = header.index('Invoiced') if 'Invoiced' in header else None
invoice_num_col_idx = header.index('Invoice #') if 'Invoice #' in header else None

if invoiced_col_idx is None or invoice_num_col_idx is None:
    print("Error: Could not find Invoiced or Invoice # columns")
    sys.exit(1)

# Find rows for the specified month
target_rows = []
for idx, row in enumerate(all_data[3:], start=4):  # Data starts at row 4 (index 3)
    month_val = row[0] if len(row) > 0 else ''  # Month column
    
    if month_val == month_name:
        target_rows.append(idx)

# Update both columns for all March rows
if target_rows:
    for row_idx in target_rows:
        # Update Invoiced column to Yes
        ws.update_cell(row_idx, invoiced_col_idx + 1, 'Yes')
        # Update Invoice # column
        ws.update_cell(row_idx, invoice_num_col_idx + 1, invoice_number)
    
    print(f'Updated {len(target_rows)} {month_name} rows:')
    print(f'  - Marked as Invoiced: Yes')
    print(f'  - Invoice #: {invoice_number}')
else:
    print(f'No {month_name} rows found to update')
