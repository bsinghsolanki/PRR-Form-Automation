import os
# from dotenv import load_dotenv

# load_dotenv()

# ── Google Sheets ──────────────────────────────────────
GOOGLE_SHEET_ID        = os.getenv("GOOGLE_SHEET_ID", "1tPVwjc-UkupQibXsGur2StClfrIlWcyRlyMnLECepNg")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SHEET_NAME             = os.getenv("SHEET_NAME", "test sheet")

# ── Browser ────────────────────────────────────────────
HEADLESS             = os.getenv("HEADLESS", "False").lower() == "true"
BROWSER              = os.getenv("BROWSER", "chrome").lower()
PAGE_LOAD_TIMEOUT    = int(os.getenv("PAGE_LOAD_TIMEOUT", 30))
ELEMENT_WAIT_TIMEOUT = int(os.getenv("ELEMENT_WAIT_TIMEOUT", 15))

# ── Retry ──────────────────────────────────────────────
MAX_RETRIES  = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY  = int(os.getenv("RETRY_DELAY", 2))

# ── Paths ──────────────────────────────────────────────
SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")
RESULTS_CSV    = os.getenv("RESULTS_CSV", "reports/results.csv")

# ── XPath ──────────────────────────────────────────────
# ── XPath for tile selection ───────────────────────
TILE_XPATH = (
    '//span[@class="tile-title"]'
    '/h3[contains(text(),"General Records") or '
    'contains(text(),"Public Records")]'
)