import os
import csv
from datetime import datetime
from typing import List, Optional
import gspread
from google.oauth2.service_account import Credentials
from models.record import Record
from config.settings import (
    GOOGLE_SHEET_ID,
    GOOGLE_CREDENTIALS_FILE,
    SHEET_NAME,
    RESULTS_CSV,
)
from utils.logger import get_logger

log = get_logger(__name__)

# ── Google Sheets API scopes ───────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Result columns written back to sheet ──────────────
RESULT_COLUMNS = {
    "status"          : "Status",
    "error_message"   : "Error Message",
    "screenshot_path" : "Screenshot",
    "timestamp"       : "Last Run",
}


class ResultWriter:
    """
    Writes automation results back to:
      - Google Sheet  (appends Status, Error, Screenshot columns)
      - Local CSV     (always written as backup)

    Usage:
        writer = ResultWriter()
        writer.write(records)                  # Write all at end
        writer.write_single(record)            # Write one row live
        writer.print_summary(records)          # Print console summary
    """

    def __init__(self, write_to_sheet: bool = True):
        """
        Args:
            write_to_sheet : If True, writes results back to Google Sheet.
                             Set False to only write CSV.
        """
        self.write_to_sheet = write_to_sheet
        self.client         = None
        self.worksheet      = None

        # Ensure CSV output folder exists
        os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)

        if write_to_sheet:
            self._authenticate()
            self._open_worksheet()

    # ─────────────────────────────────────────────────
    # AUTHENTICATION
    # ─────────────────────────────────────────────────

    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        try:
            creds = Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE,
                scopes=SCOPES
            )
            self.client = gspread.authorize(creds)
            log.info("✅ ResultWriter authenticated with Google Sheets")
        except Exception as e:
            log.warning(
                f"⚠️  Google Sheets auth failed — "
                f"results will only be written to CSV → {e}"
            )
            self.write_to_sheet = False

    def _open_worksheet(self):
        """Open the target worksheet."""
        try:
            spreadsheet    = self.client.open_by_key(GOOGLE_SHEET_ID)
            self.worksheet = spreadsheet.worksheet(SHEET_NAME)
            log.info(f"✅ Worksheet '{SHEET_NAME}' opened for result writing")
        except Exception as e:
            log.warning(
                f"⚠️  Could not open worksheet — "
                f"results will only be written to CSV → {e}"
            )
            self.write_to_sheet = False

    # ─────────────────────────────────────────────────
    # ENSURE RESULT COLUMNS EXIST IN SHEET
    # ─────────────────────────────────────────────────

    def _ensure_result_columns(self) -> dict:
        """
        Check if result columns exist in sheet header row.
        Add them if they don't exist.

        Returns:
            dict mapping column_name → column_index (1-based)
        """
        try:
            header_row    = self.worksheet.row_values(1)
            column_indices = {}

            for col_key, col_name in RESULT_COLUMNS.items():
                if col_name in header_row:
                    column_indices[col_key] = header_row.index(col_name) + 1
                else:
                    # Append new column header at end
                    new_col_index = len(header_row) + 1
                    self.worksheet.update_cell(1, new_col_index, col_name)
                    header_row.append(col_name)
                    column_indices[col_key] = new_col_index
                    log.info(f"➕ Added result column '{col_name}' at position {new_col_index}")

            return column_indices

        except Exception as e:
            log.warning(f"⚠️  Could not ensure result columns → {e}")
            return {}

    # ─────────────────────────────────────────────────
    # WRITE SINGLE RECORD TO SHEET
    # ─────────────────────────────────────────────────

    def write_single(self, record: Record) -> bool:
        """
        Write result for a single record back to its sheet row.
        Call this immediately after each record is processed
        so results are saved live (not just at end).

        Args:
            record : Processed Record with status populated

        Returns:
            True if written successfully, False otherwise
        """
        # Always write to CSV
        self._append_to_csv(record)

        # Write to sheet if enabled
        if not self.write_to_sheet or not self.worksheet:
            return False

        try:
            column_indices = self._ensure_result_columns()
            if not column_indices:
                return False

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            updates = {
                "status"          : record.status.upper(),
                "error_message"   : record.error_message or "",
                "screenshot_path" : record.screenshot_path or "",
                "timestamp"       : timestamp,
            }

            for col_key, value in updates.items():
                col_index = column_indices.get(col_key)
                if col_index:
                    self.worksheet.update_cell(
                        record.row_number,
                        col_index,
                        value
                    )

            log.info(
                f"📊 [Row {record.row_number}] "
                f"Result written to sheet: {record.status.upper()}"
            )
            return True

        except Exception as e:
            log.warning(
                f"⚠️  [Row {record.row_number}] "
                f"Failed to write result to sheet → {e}"
            )
            return False

    # ─────────────────────────────────────────────────
    # WRITE ALL RECORDS TO SHEET
    # ─────────────────────────────────────────────────

    def write(self, records: List[Record]) -> None:
        """
        Write results for all records at once.
        Use this at the end of a full run.

        Args:
            records : All processed Record objects
        """
        log.info(f"📊 Writing results for {len(records)} records …")

        for record in records:
            self.write_single(record)

        log.info("✅ All results written")

    # ─────────────────────────────────────────────────
    # CSV BACKUP
    # ─────────────────────────────────────────────────

    def _append_to_csv(self, record: Record) -> None:
        """
        Append a single record's result to the CSV file.
        CSV is always written regardless of sheet write status.
        """
        try:
            file_exists = os.path.exists(RESULTS_CSV)

            with open(RESULTS_CSV, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "row_number",
                        "url",
                        "email",
                        "status",
                        "error_message",
                        "screenshot_path",
                        "timestamp",
                    ]
                )

                # Write header only on first write
                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    "row_number"      : record.row_number,
                    "url"             : record.url,
                    "email"           : record.email,
                    "status"          : record.status.upper(),
                    "error_message"   : record.error_message or "",
                    "screenshot_path" : record.screenshot_path or "",
                    "timestamp"       : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

        except Exception as e:
            log.warning(f"⚠️  CSV write failed for row {record.row_number} → {e}")

    # ─────────────────────────────────────────────────
    # PRINT SUMMARY
    # ─────────────────────────────────────────────────

    def print_summary(self, records: List[Record]) -> None:
        """
        Print a clean summary table to the console after the run.

        Args:
            records : All processed Record objects
        """
        total   = len(records)
        success = sum(1 for r in records if r.status == "success")
        failed  = sum(1 for r in records if r.status == "failed")
        pending = sum(1 for r in records if r.status == "pending")

        log.info("=" * 60)
        log.info("📊  AUTOMATION RUN SUMMARY")
        log.info("=" * 60)
        log.info(f"  Total Rows   : {total}")
        log.info(f"  ✅ Success   : {success}")
        log.info(f"  ❌ Failed    : {failed}")
        log.info(f"  ⏳ Pending   : {pending}")
        log.info("=" * 60)

        # Detail failed rows
        failed_records = [r for r in records if r.status == "failed"]
        if failed_records:
            log.info("  ❌ FAILED ROWS:")
            for r in failed_records:
                log.info(
                    f"     Row {r.row_number} | {r.url[:40]} | "
                    f"{r.error_message[:50] if r.error_message else 'No reason'}"
                )
            log.info("=" * 60)

        log.info(f"  📁 CSV Results : {RESULTS_CSV}")
        log.info(f"  📸 Screenshots : screenshots/")
        log.info("=" * 60)

    # ─────────────────────────────────────────────────
    # WRITE FAILED ONLY
    # ─────────────────────────────────────────────────

    def write_failed_report(
        self,
        records: List[Record],
        output_path: Optional[str] = None
    ) -> str:
        """
        Write a separate CSV containing only failed records.
        Useful for re-running failed rows without reprocessing all.

        Args:
            records     : All processed records
            output_path : Custom path for failed report CSV

        Returns:
            Path to the failed records CSV
        """
        failed_records = [r for r in records if r.status == "failed"]

        if not failed_records:
            log.info("✅ No failed records — skipping failed report")
            return ""

        path = output_path or RESULTS_CSV.replace(".csv", "_failed.csv")

        try:
            with open(path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "row_number", "url", "email",
                        "password", "description",
                        "preferred_method", "acknowledgment",
                        "error_message", "screenshot_path",
                    ]
                )
                writer.writeheader()

                for r in failed_records:
                    writer.writerow({
                        "row_number"       : r.row_number,
                        "url"              : r.url,
                        "email"            : r.email,
                        "password"         : r.password,
                        "description"      : r.description,
                        "preferred_method" : r.preferred_method,
                        "acknowledgment"   : r.acknowledgment,
                        "error_message"    : r.error_message or "",
                        "screenshot_path"  : r.screenshot_path or "",
                    })

            log.info(
                f"📄 Failed records report saved → {path} "
                f"({len(failed_records)} rows)"
            )
            return path

        except Exception as e:
            log.error(f"❌ Failed to write failed report → {e}")
            return ""