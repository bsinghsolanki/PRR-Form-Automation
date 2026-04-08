import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Sheet2 columns — Description excluded intentionally
SHEET2_HEADERS = [
    "Agency Name",
    "Org ID",
    "Dataset Owner",
    "Dataset Number",
    "Dataset",
    "First Name",
    "Last Name",
    "Processor",
    "Portal URL",
    "Name",
    "Phone",
    "Street Address",
    "City",
    "State",
    "Zip",
    "Company",
    "Email",
    "Status",       # set by bot: "Filled" | "Not Filled"
    "Error",        # set by bot: blank on success, message on failure
    "Timestamp",    # set by bot: when the row was processed
]

# Map Sheet2 header → Sheet1 normalised key (lowercase)
SHEET1_KEY_MAP = {
    "Agency Name":    "agency name",
    "Org ID":         "org id",
    "Dataset Owner":  "dataset owner",
    "Dataset Number": "dataset number",
    "Dataset":        "dataset",
    "First Name":     "first name",
    "Last Name":      "last name",
    "Processor":      "processor",
    "Portal URL":     "portal url",
    "Name":           "name",
    "Phone":          "phone",
    "Street Address": "street address",
    "City":           "city",
    "State":          "state",
    "Zip":            "zip",
    "Company":        "company",
    "Email":          "email",
}


def _get_client(credentials_file):
    creds = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
    return gspread.authorize(creds)


def load_rows(credentials_file, sheet_id, worksheet_name):

    client = _get_client(credentials_file)
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)
    records = worksheet.get_all_records()

    normalized_records = []
    for row in records:
        normalized_row = {
            key.strip().lower(): value
            for key, value in row.items()
        }
        normalized_records.append(normalized_row)

    return normalized_records


def update_status(credentials_file, sheet_id, row_data, status, error=""):
    """
    Append one result row to Sheet2 (auto-created if missing).

    Args:
        credentials_file : path to service account JSON
        sheet_id         : Google Sheet ID
        row_data         : normalised row dict from Sheet1
        status           : "Filled" | "Not Filled"
        error            : error message string (empty on success)
    """
    try:
        client = _get_client(credentials_file)
        sheet  = client.open_by_key(sheet_id)

        # ── Get or create Sheet2 ────────────────────────────────────────
        try:
            ws = sheet.worksheet("Sheet2")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Sheet2", rows=5000, cols=len(SHEET2_HEADERS))
            ws.append_row(SHEET2_HEADERS, value_input_option="RAW")
            ws.format(f"A1:{chr(64 + len(SHEET2_HEADERS))}1", {"textFormat": {"bold": True}})
            ws.freeze(rows=1)
            print("📋 Sheet2 created with headers")

        # ── Build row ───────────────────────────────────────────────────
        new_row = []
        for header in SHEET2_HEADERS:
            if header == "Status":
                new_row.append(status)
            elif header == "Error":
                new_row.append(str(error)[:500] if error else "")
            elif header == "Timestamp":
                new_row.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                sheet1_key = SHEET1_KEY_MAP.get(header, header.lower())
                new_row.append(str(row_data.get(sheet1_key, "")))

        ws.append_row(new_row, value_input_option="RAW")

        # ── Colour-code the Status cell ─────────────────────────────────
        last_row   = len(ws.get_all_values())
        status_col = SHEET2_HEADERS.index("Status") + 1
        status_cell = gspread.utils.rowcol_to_a1(last_row, status_col)

        color = (
            {"red": 0.2, "green": 0.78, "blue": 0.35}
            if status == "Filled"
            else {"red": 0.92, "green": 0.26, "blue": 0.21}
        )
        ws.format(status_cell, {
            "backgroundColor": color,
            "textFormat": {"bold": True},
        })

        print(f"📊 Sheet2 updated → {row_data.get('agency name', row_data.get('portal url', '?'))}: {status}")

    except Exception as e:
        print(f"⚠️  Could not update Sheet2: {e}")