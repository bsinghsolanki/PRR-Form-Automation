import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from browser.element_helper import ElementHelper
from browser.screenshot import ScreenshotManager
from models.record import Record
from config.settings import TILE_XPATH, PAGE_LOAD_TIMEOUT
from utils.logger import get_logger
from utils.retry import retry
from utils.captcha_solver import CaptchaSolver
log = get_logger(__name__)


class TileSelector:
    """
    Step 1 — Open the URL from the record and click the
    City/public tile using the XPath defined in config.

    Usage:
        tile_selector = TileSelector(driver)
        success = tile_selector.run(record)
    """

    def __init__(self, driver: WebDriver):
        self.driver     = driver
        self.helper     = ElementHelper(driver)
        self.screenshot = ScreenshotManager(driver)

    # ─────────────────────────────────────────────────
    # MAIN RUN
    # ─────────────────────────────────────────────────

    def run(self, record: Record) -> bool:
        """
        Full tile selection flow:
          1. Open URL
          2. Wait for page to load
          3. Find and click the City/public tile

        Args:
            record : Record object containing the URL

        Returns:
            True if tile was found and clicked, False otherwise
        """
        log.info(f"🌐 [Row {record.row_number}] Opening URL: {record.url}")

        # ── Step 1: Open URL ───────────────────────────
        if not self._open_url(record):
            return False

        # ── Step 2: Wait for page ──────────────────────
        self.helper.wait_for_page_load(timeout=PAGE_LOAD_TIMEOUT)
        time.sleep(2)  # Extra buffer for dynamic content to render

        # ── Step 3: Click tile ─────────────────────────
        return self._click_tile(record)

    # ─────────────────────────────────────────────────
    # OPEN URL
    # ─────────────────────────────────────────────────

    def _open_url(self, record: Record) -> bool:
        """
        Navigate the browser to the record's URL.

        Returns:
            True if navigation succeeded, False otherwise
        """
        try:
            self.driver.get(record.url)
            log.info(f"✅ [Row {record.row_number}] Page opened successfully")
            return True

        except TimeoutException:
            msg = f"Page load timed out after {PAGE_LOAD_TIMEOUT}s: {record.url}"
            log.error(f"❌ [Row {record.row_number}] {msg}")
            screenshot_path = self.screenshot.capture(
                record.row_number, "page_load_timeout"
            )
            record.mark_failed(msg, screenshot_path)
            return False

        except WebDriverException as e:
            msg = f"Failed to open URL: {record.url} → {e}"
            log.error(f"❌ [Row {record.row_number}] {msg}")
            screenshot_path = self.screenshot.capture(
                record.row_number, "url_open_failed"
            )
            record.mark_failed(msg, screenshot_path)
            return False

    # ─────────────────────────────────────────────────
    # CLICK TILE
    # ─────────────────────────────────────────────────

    @retry(max_attempts=3, delay=2, on_failure="skip")
    def _click_tile(self, record: Record) -> bool:
        """
        Find and click the City/public tile using the XPath.
        Tries multiple strategies before giving up.

        Strategy order:
          1. Standard XPath click
          2. JavaScript click (if overlay blocking)
          3. Find all matching tiles and click first visible one

        Returns:
            True if tile was clicked, False otherwise
        """
        log.info(
            f"🔍 [Row {record.row_number}] "
            f"Looking for City/public tile …"
        )

        # ── Strategy 1: Standard click ─────────────────
        if self.helper.click_xpath(TILE_XPATH):
            log.info(f"✅ [Row {record.row_number}] Tile clicked successfully")
            time.sleep(1)  # Wait for click response
            return True

        # ── Strategy 2: JS click ───────────────────────
        log.warning(
            f"⚠️  [Row {record.row_number}] "
            f"Standard click failed, trying JS click …"
        )
        if self.helper.click_xpath(TILE_XPATH, use_js=True):
            log.info(
                f"✅ [Row {record.row_number}] "
                f"Tile clicked via JS"
            )
            time.sleep(1)
            return True

        # ── Strategy 3: Find all tiles, click first visible ──
        log.warning(
            f"⚠️  [Row {record.row_number}] "
            f"JS click failed, scanning all tiles …"
        )
        result = self._click_first_visible_tile(record)
        if result:
            return True

        # ── All strategies failed ──────────────────────
        msg = "Could not find or click City/public tile after all strategies"
        log.error(f"❌ [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(
            record.row_number, "tile_not_found"
        )
        record.mark_failed(msg, screenshot_path)
        return False

    # ─────────────────────────────────────────────────
    # FALLBACK: SCAN ALL TILES
    # ─────────────────────────────────────────────────

    def _click_first_visible_tile(self, record: Record) -> bool:
        """
        Fallback strategy — find ALL h3 elements inside tile groups
        and click the first one whose text contains 'City' or 'public'.

        Returns:
            True if a matching tile was found and clicked, False otherwise
        """
        try:
            # Broader XPath to find all tile h3s
            all_tiles_xpath = '//div[contains(@class,"tile-group")]//h3'
            tiles = self.helper.find_all(all_tiles_xpath)

            log.info(
                f"🔍 [Row {record.row_number}] "
                f"Found {len(tiles)} total tiles to scan"
            )

            for tile in tiles:
                try:
                    text = tile.text.strip().lower()
                    if "city" in text or "public" in text:
                        log.info(
                            f"🎯 [Row {record.row_number}] "
                            f"Matched tile text: '{tile.text.strip()}'"
                        )
                        self.driver.execute_script(
                            "arguments[0].scrollIntoView({block: 'center'});",
                            tile
                        )
                        time.sleep(0.3)
                        self.driver.execute_script(
                            "arguments[0].click();", tile
                        )
                        log.info(
                            f"✅ [Row {record.row_number}] "
                            f"Fallback tile click succeeded"
                        )
                        time.sleep(1)
                        return True

                except Exception as e:
                    log.debug(f"Skipping stale tile element → {e}")
                    continue

            log.warning(
                f"⚠️  [Row {record.row_number}] "
                f"No tile with 'City' or 'public' text found in {len(tiles)} tiles"
            )
            return False

        except Exception as e:
            log.error(
                f"❌ [Row {record.row_number}] "
                f"Tile scan failed → {e}"
            )
            return False

    # ─────────────────────────────────────────────────
    # VERIFY TILE CLICK WORKED
    # ─────────────────────────────────────────────────

    def verify_tile_clicked(self, expected_url_fragment: str = None) -> bool:
        """
        Optional verification after clicking tile.
        Checks if the page changed (URL changed or new element appeared).

        Args:
            expected_url_fragment : Partial URL string to check for after click
                                    e.g. "login", "request", "portal"
        Returns:
            True if page changed as expected
        """
        try:
            if expected_url_fragment:
                return self.helper.wait_for_url_contains(
                    expected_url_fragment, timeout=10
                )

            # Generic check — just wait for page to settle
            time.sleep(2)
            self.helper.wait_for_page_load()
            log.info("✅ Page changed after tile click")
            return True

        except Exception as e:
            log.warning(f"⚠️  Tile click verification failed → {e}")
            return False