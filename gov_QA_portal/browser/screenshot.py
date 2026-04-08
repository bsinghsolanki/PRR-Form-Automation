import os
from datetime import datetime
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from config.settings import SCREENSHOT_DIR
from utils.logger import get_logger

log = get_logger(__name__)


class ScreenshotManager:
    """
    Handles capturing and saving screenshots during automation.
    Screenshots are saved to the SCREENSHOT_DIR folder defined in .env

    Usage:
        screenshot = ScreenshotManager(driver)

        # On error
        path = screenshot.capture(record.row_number, "login_failed")

        # On success (optional)
        path = screenshot.capture(record.row_number, "form_submitted", is_error=False)
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ─────────────────────────────────────────────────
    # CAPTURE
    # ─────────────────────────────────────────────────

    def capture(
        self,
        row_number: int,
        label: str = "screenshot",
        is_error: bool = True
    ) -> Optional[str]:
        """
        Capture a screenshot and save it to SCREENSHOT_DIR.

        Args:
            row_number : Spreadsheet row number (used in filename)
            label      : Short description e.g. 'login_failed', 'tile_not_found'
            is_error   : If True saves to /errors subfolder, else /success

        Returns:
            Full file path of saved screenshot, or None if capture failed
        """
        try:
            # ── Build subfolder ────────────────────────
            subfolder = "errors" if is_error else "success"
            folder    = os.path.join(SCREENSHOT_DIR, subfolder)
            os.makedirs(folder, exist_ok=True)

            # ── Build filename ─────────────────────────
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename  = f"row{row_number}_{label}_{timestamp}.png"
            filepath  = os.path.join(folder, filename)

            # ── Save screenshot ────────────────────────
            self.driver.save_screenshot(filepath)

            if is_error:
                log.error(f"📸 Error screenshot saved → {filepath}")
            else:
                log.info(f"📸 Screenshot saved → {filepath}")

            return filepath

        except Exception as e:
            log.warning(f"⚠️  Failed to capture screenshot → {e}")
            return None

    # ─────────────────────────────────────────────────
    # CAPTURE FULL PAGE
    # ─────────────────────────────────────────────────

    def capture_full_page(
        self,
        row_number: int,
        label: str = "full_page",
    ) -> Optional[str]:
        """
        Capture a full-page screenshot by temporarily
        resizing the browser window to page height.

        Returns:
            Full file path of saved screenshot, or None if failed
        """
        try:
            # ── Get full page dimensions ───────────────
            total_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )
            total_width = self.driver.execute_script(
                "return document.body.scrollWidth"
            )

            # ── Resize window to full page ─────────────
            self.driver.set_window_size(total_width, total_height)

            # ── Capture ────────────────────────────────
            filepath = self.capture(row_number, label, is_error=False)

            # ── Restore window size ────────────────────
            self.driver.maximize_window()

            return filepath

        except Exception as e:
            log.warning(f"⚠️  Full page screenshot failed → {e}")
            # Fallback to normal screenshot
            return self.capture(row_number, label)

    # ─────────────────────────────────────────────────
    # CAPTURE ON EXCEPTION
    # ─────────────────────────────────────────────────

    def capture_on_exception(
        self,
        row_number: int,
        exception: Exception,
        label: str = "exception"
    ) -> Optional[str]:
        """
        Capture a screenshot and log the exception details together.
        Designed to be called inside except blocks.

        Usage:
            try:
                helper.click_xpath(TILE_XPATH)
            except Exception as e:
                screenshot.capture_on_exception(record.row_number, e, "tile_click")

        Returns:
            Full file path of saved screenshot, or None if failed
        """
        log.error(f"💥 Exception on row {row_number}: {type(exception).__name__} → {exception}")
        return self.capture(row_number, label, is_error=True)

    # ─────────────────────────────────────────────────
    # CLEANUP OLD SCREENSHOTS
    # ─────────────────────────────────────────────────

    def cleanup_old_screenshots(self, keep_last: int = 50):
        """
        Delete oldest screenshots keeping only the most recent ones.
        Useful for long automation runs that generate many files.

        Args:
            keep_last : Number of most recent screenshots to keep
        """
        try:
            all_files = []

            for subfolder in ["errors", "success"]:
                folder = os.path.join(SCREENSHOT_DIR, subfolder)
                if os.path.exists(folder):
                    for f in os.listdir(folder):
                        if f.endswith(".png"):
                            full_path = os.path.join(folder, f)
                            all_files.append((os.path.getmtime(full_path), full_path))

            # Sort by modification time (oldest first)
            all_files.sort(key=lambda x: x[0])

            # Delete oldest beyond keep_last
            to_delete = all_files[:-keep_last] if len(all_files) > keep_last else []

            for _, filepath in to_delete:
                os.remove(filepath)
                log.debug(f"🗑️  Deleted old screenshot: {filepath}")

            if to_delete:
                log.info(f"🧹 Cleaned up {len(to_delete)} old screenshots")

        except Exception as e:
            log.warning(f"⚠️  Screenshot cleanup failed → {e}")
# ```

# ---

# **What this file does:**
# - `capture()` — saves screenshot to `screenshots/errors/` or `screenshots/success/` subfolder automatically
# - Filenames are formatted as `row3_login_failed_20240315_142301.png` so you can instantly identify what failed and when
# - `capture_full_page()` — resizes browser to full page height to capture everything, then restores window size
# - `capture_on_exception()` — designed to drop into `except` blocks, logs the exception and screenshot together
# - `cleanup_old_screenshots()` — keeps folder tidy on long runs by deleting oldest files beyond a limit

# ---

# **Screenshot folder structure after a run:**
# ```
# screenshots/
# ├── errors/
# │   ├── row2_login_failed_20240315_142301.png
# │   └── row5_tile_not_found_20240315_142455.png
# └── success/
#     └── row3_form_submitted_20240315_142350.png