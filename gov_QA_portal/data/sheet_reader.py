import os
import gspread
import pandas as pd
from typing import List, Optional
from google.oauth2.service_account import Credentials
from models.record import Record
from config.settings import (
    GOOGLE_SHEET_ID,
    GOOGLE_CREDENTIALS_FILE,
    SHEET_NAME,
)
from utils.logger import get_logger
from utils.date_extractor import extract_mrpo_date, get_today
from urllib.parse import urlparse

log = get_logger(__name__)

# ── Google Sheets API scopes ───────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Expected column names in your spreadsheet ──────────
# Adjust these to exactly match your sheet's header row
COLUMN_MAP = {
    # ── Navigation ─────────────────────────────────────
    "url"              : "Portal URL",

    # ── Login ──────────────────────────────────────────
    "email"            : "Email",
    "password"         : "Password",

    # ── Form Fields ────────────────────────────────────
    "description"      : "Description",
    "content_type"     : "Content Type",
    "status_details"   : "Status Details",

    # ── Personal / Company Info ─────────────────────────
    "first_name"       : "Name",
    "phone"            : "Phone",
    "address"          : "Street Address",
    "city"             : "City",
    "state"            : "State",
    "zip_code"         : "Zip",
    "company"          : "Company",

    # ── Account / Organization Meta ────────────────────
    "account_name"     : "Account Name",
    "org_id"           : "Organization ID",
    "account_state"    : "Account State",
    "dataset_number"   : "Data Set Number",
    "dataset_owner"    : "Owner Name",
    "processor"        : "Processor",
}


class SheetReader:
    """
    Reads rows from a Google Sheet or local Excel/CSV file
    and returns a list of Record objects.

    Usage:
        reader  = SheetReader()
        records = reader.get_records()
    """

    def __init__(self, use_local: bool = False, local_path: Optional[str] = None):
        """
        Args:
            use_local  : If True, reads from a local Excel/CSV instead of Google Sheets
            local_path : Path to local .xlsx or .csv file (required if use_local=True)
        """
        self.use_local  = use_local
        self.local_path = local_path
        self.client     = None

        if not use_local:
            self._authenticate()

    # ── Authentication ─────────────────────────────────
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account credentials."""
        try:
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            log.info("✅ Google Sheets authenticated successfully")
        except FileNotFoundError:
            log.error(
                f"❌ Credentials file not found: '{GOOGLE_CREDENTIALS_FILE}'. "
                "Download it from Google Cloud Console and place it in the project root."
            )
            raise
        except Exception as e:
            log.error(f"❌ Google Sheets authentication failed → {e}")
            raise

    # ── Fetch raw data ─────────────────────────────────
    def _fetch_from_google_sheet(self) -> pd.DataFrame:
        """Open the Google Sheet and return all rows as a DataFrame."""
        try:
            log.info(f"📄 Opening Google Sheet ID: {GOOGLE_SHEET_ID}")
            spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)
            worksheet   = spreadsheet.worksheet(SHEET_NAME)
            data        = worksheet.get_all_records()  # list of dicts (header → value)

            if not data:
                log.warning("⚠️  Sheet is empty or has no data rows.")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            log.info(f"✅ Loaded {len(df)} rows from sheet '{SHEET_NAME}'")
            return df

        except gspread.exceptions.SpreadsheetNotFound:
            log.error(f"❌ Spreadsheet not found. Check GOOGLE_SHEET_ID in .env")
            raise
        except gspread.exceptions.WorksheetNotFound:
            log.error(f"❌ Sheet tab '{SHEET_NAME}' not found. Check SHEET_NAME in .env")
            raise

    def _fetch_from_local(self) -> pd.DataFrame:
        """Read from a local Excel or CSV file."""
        if not self.local_path or not os.path.exists(self.local_path):
            log.error(f"❌ Local file not found: '{self.local_path}'")
            raise FileNotFoundError(f"File not found: {self.local_path}")

        ext = os.path.splitext(self.local_path)[-1].lower()

        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(self.local_path)
            log.info(f"✅ Loaded {len(df)} rows from Excel: {self.local_path}")
        elif ext == ".csv":
            df = pd.read_csv(self.local_path)
            log.info(f"✅ Loaded {len(df)} rows from CSV: {self.local_path}")
        else:
            raise ValueError(f"Unsupported file type: {ext}. Use .xlsx or .csv")

        return df

    # ── Row → Record ───────────────────────────────────
    def _row_to_record(self, row: pd.Series, row_number: int) -> Optional[Record]:
      def get(col_key: str) -> str:
          col_name = COLUMN_MAP.get(col_key, col_key)
          value    = row.get(col_name, "")
          return str(value).strip() if pd.notna(value) else ""

      # ── Only these 3 are truly required ────────────────
      required = ["url", "email", "password"]
      missing  = [f for f in required if not get(f)]

      if missing:
          log.warning(
              f"⚠️  Row {row_number} skipped — missing required fields: "
              f"{[COLUMN_MAP[f] for f in missing]}"
          )
          return None

      # ── Extract domain from URL BEFORE creating Record ─
      from urllib.parse import urlparse
      raw_url    = get("url")
      parsed_url = urlparse(raw_url)
      domain     = f"{parsed_url.scheme}://{parsed_url.netloc}"
      log.info(f"🌐 Row {row_number} domain: {domain}")

      # ── Split Name into first/last if possible ─────────
      full_name  = get("first_name")
      name_parts = full_name.split(" ", 1) if full_name else ["", ""]
      first_name = name_parts[0] if len(name_parts) > 0 else ""
      last_name  = name_parts[1] if len(name_parts) > 1 else ""

      record = Record(
          row_number = row_number,

          # ── Required ───────────────────────────────────
          url        = raw_url,        # ← use raw_url instead of get("url")
          email      = get("email"),
          password   = get("password"),

          # ── Domain (auto extracted from URL) ───────────
          domain     = domain,         # ← pass domain directly here

          # ── Description ────────────────────────────────
          description = get("description") or get("content_type") or "",

          # ── Hardcoded form defaults ────────────────────
          preferred_method      = "Electronic",
          acknowledgment        = "Yes",
          records_requested_for = "Commercial purpose",
          type_of_records       = get("content_type") or "Finance",
          department            = "Admin",

          # ── Address (sheet first, fallback to default) ──
          address  = get("address")  or "5000 T-Rex Ave Suite 200",
          city     = get("city")     or "Boca Raton",
          state    = get("state")    or "FL",
          zip_code = get("zip_code") or "33431",

          # ── Personal info ──────────────────────────────
          first_name = first_name or None,
          last_name  = last_name  or None,
          phone      = get("phone") or None,
          company    = get("company") or None,

          # ── Meta (for logging/reference) ───────────────
          account_name   = get("account_name")   or None,
          org_id         = get("org_id")         or None,
          account_state  = get("account_state")  or None,
          dataset_number = get("dataset_number") or None,
          dataset_owner  = get("dataset_owner")  or None,
          processor      = get("processor")      or None,
          status_details = get("status_details") or None,
      )
      if record.date_from:
        log.info(
            f"📅 Row {row_number} MRPO date: "
            f"{record.date_from} → {record.date_to}"
        )

      log.info(f"✅ Row {row_number} loaded: {record.url[:40]} | {record.email}")
      return record

    # ── Public method ──────────────────────────────────
    def get_records(self) -> List[Record]:
        """
        Main method — fetch sheet data and return a list of valid Record objects.

        Returns:
            List[Record]: One Record per valid spreadsheet row
        """
        df = (
            self._fetch_from_local()
            if self.use_local
            else self._fetch_from_google_sheet()
        )

        if df.empty:
            log.warning("⚠️  No data found. Returning empty list.")
            return []

        records = []
        for i, (_, row) in enumerate(df.iterrows(), start=2):  # start=2 (row 1 = header)
            record = self._row_to_record(row, row_number=i)
            if record:
                records.append(record)

        log.info(f"📋 {len(records)} valid records ready for processing")
        
        return records