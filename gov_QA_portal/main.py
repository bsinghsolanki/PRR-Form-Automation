import time
import argparse
import sys
from typing import List, Optional

from data.sheet_reader import SheetReader
from browser.driver_setup import DriverSetup
from steps.tile_selector import TileSelector
from steps.login_handler import LoginHandler
from steps.form_filler import FormFiller
from reports.result_writer import ResultWriter
from models.record import Record
from utils.logger import get_logger

log = get_logger(__name__)


def parse_args():
    """
    Parse command line arguments for flexible run control.

    Examples:
        python main.py
        python main.py --local data/sheet.xlsx
        python main.py --rows 2 5 7
        python main.py --start-row 3
        python main.py --dry-run
        python main.py --no-sheet
    """
    parser = argparse.ArgumentParser(
        description="Form Automation — Reads sheet data and fills forms via Selenium"
    )

    parser.add_argument(
        "--local",
        type=str,
        default=None,
        help="Path to local Excel/CSV file instead of Google Sheet (e.g. data/sheet.xlsx)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        nargs="+",
        default=None,
        help="Only process specific row numbers (e.g. --rows 2 5 7)"
    )
    parser.add_argument(
        "--start-row",
        type=int,
        default=None,
        help="Start processing from this row number onwards (e.g. --start-row 5)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and validate sheet data without opening browser"
    )
    parser.add_argument(
        "--no-sheet",
        action="store_true",
        help="Do not write results back to Google Sheet (CSV only)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between processing each row (default: 2.0)"
    )

    return parser.parse_args()


# ─────────────────────────────────────────────────────
# FILTER RECORDS
# ─────────────────────────────────────────────────────

def filter_records(
    records: List[Record],
    rows: Optional[List[int]],
    start_row: Optional[int]
) -> List[Record]:
    """
    Filter records based on CLI arguments.

    Args:
        records   : Full list of records from sheet
        rows      : Specific row numbers to process
        start_row : Only process rows >= this number

    Returns:
        Filtered list of records
    """
    if rows:
        filtered = [r for r in records if r.row_number in rows]
        log.info(f"🎯 Filtered to specific rows: {rows} → {len(filtered)} records")
        return filtered

    if start_row:
        filtered = [r for r in records if r.row_number >= start_row]
        log.info(
            f"🎯 Filtered from row {start_row} onwards → {len(filtered)} records"
        )
        return filtered

    return records


# ─────────────────────────────────────────────────────
# DRY RUN
# ─────────────────────────────────────────────────────

def dry_run(records: List[Record]) -> None:
    """
    Validate and display all records without opening browser.
    Useful for checking sheet data before a real run.
    """
    log.info("🧪 DRY RUN MODE — No browser will be opened")
    log.info("=" * 60)

    for record in records:
        log.info(
            f"  Row {record.row_number:>3} | "
            f"URL: {record.url[:35]:<35} | "
            f"Email: {record.email[:25]:<25} | "
            f"Method: {record.preferred_method}"
        )

    log.info("=" * 60)
    log.info(f"✅ {len(records)} records validated — ready to run")


# ─────────────────────────────────────────────────────
# PROCESS SINGLE RECORD
# ─────────────────────────────────────────────────────

def process_record(
    record          : Record,
    tile_selector   : TileSelector,
    login_handler   : LoginHandler,
    form_filler     : FormFiller,
    result_writer   : ResultWriter,    # ← ADD result_writer
) -> bool:
    """
    Run all 3 automation steps for a single record.

    Steps:
        1. Open URL and click City/public tile
        2. Login with email and password
        3. Fill and submit the form
    """
    log.info("─" * 60)
    log.info(
        f"▶️  Processing Row {record.row_number} | "
        f"{record.url[:50]} | {record.email}"
    )
    log.info("─" * 60)

    try:
        # ── Step 1: Open URL and click tile ───────────
        log.info(f"[1/3] 🌐 Tile Selection — Row {record.row_number}")
        if not tile_selector.run(record):
            log.error(
                f"❌ [Row {record.row_number}] "
                f"Step 1 (Tile Selection) failed — skipping row"
            )
            result_writer.write_single(record)
            return False

        time.sleep(1.5)

        # ── Step 2: Login ──────────────────────────────
        log.info(f"[2/3] 🔐 Login — Row {record.row_number}")
        if not login_handler.run(record):
            log.error(
                f"❌ [Row {record.row_number}] "
                f"Step 2 (Login) failed — skipping row"
            )
            result_writer.write_single(record)
            return False

        time.sleep(1.5)

        # ── Step 3: Fill form ──────────────────────────
        log.info(f"[3/3] 📝 Form Fill — Row {record.row_number}")
        if not form_filler.run(record):
            log.error(
                f"❌ [Row {record.row_number}] "
                f"Step 3 (Form Fill) failed — skipping row"
            )
            result_writer.write_single(record)
            return False

        # ── All steps passed ───────────────────────────
        log.info(
            f"✅ [Row {record.row_number}] "
            f"All steps completed successfully"
        )
        result_writer.write_single(record)
        return True

    except Exception as e:
        msg = f"Unexpected error on row {record.row_number} → {e}"
        log.error(f"💥 {msg}")
        record.mark_failed(msg)
        result_writer.write_single(record)
        return False


# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

def main():
    args = parse_args()

    log.info("=" * 60)
    log.info("🤖  FORM AUTOMATION STARTING")
    log.info("=" * 60)

    # ── Step A: Load records from sheet ───────────────
    log.info("📄 Loading records from sheet …")
    try:
        reader = SheetReader(
            use_local  = args.local is not None,
            local_path = args.local
        )
        records = reader.get_records()
    except Exception as e:
        log.error(f"❌ Failed to load sheet data → {e}")
        sys.exit(1)

    if not records:
        log.warning("⚠️  No valid records found. Exiting.")
        sys.exit(0)

    # ── Step B: Filter records ─────────────────────────
    records = filter_records(records, args.rows, args.start_row)

    if not records:
        log.warning("⚠️  No records after filtering. Exiting.")
        sys.exit(0)

    log.info(f"📋 {len(records)} records queued for processing")

    # ── Step C: Dry run mode ───────────────────────────
    if args.dry_run:
        dry_run(records)
        sys.exit(0)

    # ── Step D: Init result writer ─────────────────────
    result_writer = ResultWriter(
        write_to_sheet=not args.no_sheet
    )

    # ── Step E: Init browser and steps ────────────────
    # ── Step E: Init browser and steps ────────────────
    driver_setup  = DriverSetup()
    driver        = driver_setup.get_driver()

    tile_selector = TileSelector(driver)
    login_handler = LoginHandler(driver)
    form_filler   = FormFiller(driver)
    # captcha is handled inside form_filler automatically

    # ── Step F: Process each record ───────────────────
    success_count = 0
    failed_count  = 0

    try:
        for index, record in enumerate(records, start=1):
            log.info(
                f"\n🔄 Record {index}/{len(records)} — "
                f"Row {record.row_number}"
            )

            success = process_record(
                record,
                tile_selector,
                login_handler,
                form_filler,
                result_writer,
            )

            if success:
                success_count += 1
            else:
                failed_count += 1

            if index < len(records):
                log.info(f"⏳ Waiting {args.delay}s before next record …")
                time.sleep(args.delay)

    except KeyboardInterrupt:
        log.warning("\n⚠️  Run interrupted by user (Ctrl+C)")

    finally:
        # ── Step G: Always close browser ──────────────
        log.info("🔒 Closing browser …")
        driver_setup.quit()

        # ── Step H: Write final reports ───────────────
        log.info("📊 Writing final reports …")
        result_writer.write_failed_report(records)
        result_writer.print_summary(records)

        log.info("=" * 60)
        log.info(
            f"🏁 RUN COMPLETE — "
            f"✅ {success_count} succeeded | "
            f"❌ {failed_count} failed"
        )
        log.info("=" * 60)


if __name__ == "__main__":
    main()