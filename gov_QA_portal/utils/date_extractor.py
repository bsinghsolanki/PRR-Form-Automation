import re
from datetime import datetime
from typing import Optional

# ── Date patterns to search for in description ────────
DATE_PATTERNS = [
    r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
    r'\b(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\b',
    r'\b((?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
    r'\b(\d{1,2}[\/\-](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\/\-]\d{4})\b',
    r'\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{4})\b',
]

# ── Date formats to try when parsing ──────────────────
DATE_FORMATS = [
    "%m/%d/%Y", "%m-%d-%Y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%B %d, %Y", "%B %d %Y",
    "%b %d, %Y", "%b %d %Y",
    "%d-%b-%Y", "%d/%b/%Y",
]

# ── MRPO keyword triggers ─────────────────────────────
MRPO_KEYWORDS = [
    r'MRPO[:\s#-]*',
    r'MR\s*PO[:\s#-]*',
    r'PO[:\s#-]*(?:date)?[:\s]*',
    r'Purchase\s*Order[:\s#-]*',
    r'effective[:\s]*(?:date)?[:\s]*',
    r'from[:\s]*(?:date)?[:\s]*',
    r'start[:\s]*(?:date)?[:\s]*',
]


def extract_mrpo_date(description: str) -> Optional[str]:
    """
    Extract the MRPO date from a description string.
    Returns date formatted as MM/DD/YYYY or None if not found.
    """
    if not description:
        return None

    # ── Strategy 1: Find date after MRPO keyword ──────
    for keyword in MRPO_KEYWORDS:
        for date_pattern in DATE_PATTERNS:
            combined = rf'(?i){keyword}\s*({date_pattern[2:-2]})'
            match = re.search(combined, description)
            if match:
                raw_date = match.group(1).strip()
                parsed   = _parse_date(raw_date)
                if parsed:
                    return parsed

    # ── Strategy 2: First date found in description ────
    for date_pattern in DATE_PATTERNS:
        match = re.search(date_pattern, description)
        if match:
            raw_date = match.group(1).strip()
            parsed   = _parse_date(raw_date)
            if parsed:
                return parsed

    return None


def get_today() -> str:
    """Return today's date as MM/DD/YYYY string."""
    return datetime.today().strftime("%m/%d/%Y")


def _parse_date(raw: str) -> Optional[str]:
    """Try to parse a raw date string into MM/DD/YYYY format."""
    raw = raw.strip().rstrip(",")
    for fmt in DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return None