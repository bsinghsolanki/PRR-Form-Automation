from dataclasses import dataclass
from typing import Optional


@dataclass
class Record:
    # ── Required fields FIRST (no defaults) ───────────
    row_number : int
    url        : str
    email      : str
    password   : str

    # ── Optional fields AFTER (with defaults) ─────────

    # Navigation
    domain     : str = ""

    # Core Form Fields
    description           : str = ""
    preferred_method      : str = "Electronic"
    acknowledgment        : str = "Yes"
    records_requested_for : str = "Commercial purpose"
    type_of_records       : str = "Finance"
    department            : str = "Admin"

    # Address
    address  : str = "5000 T-Rex Ave Suite 200"
    city     : str = "Boca Raton"
    state    : str = "FL"
    zip_code : str = "33431"

    # Personal Info
    first_name : Optional[str] = None
    last_name  : Optional[str] = None
    phone      : Optional[str] = None
    company    : Optional[str] = None

    # Date Fields
    date_from : Optional[str] = None
    date_to   : Optional[str] = None

    # Account / Meta Fields
    account_name   : Optional[str] = None
    org_id         : Optional[str] = None
    account_state  : Optional[str] = None
    dataset_number : Optional[str] = None
    dataset_owner  : Optional[str] = None
    processor      : Optional[str] = None
    status_details : Optional[str] = None
    content_type   : Optional[str] = None

    # Result Tracking
    status           : str          = "pending"
    error_message    : Optional[str] = None
    screenshot_path  : Optional[str] = None

    def mark_success(self):
        self.status       = "success"
        self.error_message = None

    def mark_failed(self, reason: str, screenshot: Optional[str] = None):
        self.status          = "failed"
        self.error_message   = reason
        self.screenshot_path = screenshot

    def __str__(self):
        return (
            f"Record(row={self.row_number}, url={self.url}, "
            f"email={self.email}, status={self.status})"
        )