import gspread
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(
    "/home/adefilippo/.config/gcloud/simplifyops-co-1cf850b44c9a.json",
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
)
client = gspread.authorize(creds)
sheet = client.open_by_key("1JDcpPrDA-kNOrL58L8t0e-YL7un0esXP3XfFuYfmqnw")

# Read first worksheet
ws = sheet.worksheet("Nate - ManagePro")
print("Headers:", ws.row_values(1))
print("\nFirst 3 data rows:")
for row in ws.get_all_values()[1:4]:
    print(row)
