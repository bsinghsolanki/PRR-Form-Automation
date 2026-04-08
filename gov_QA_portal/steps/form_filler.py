import time
from selenium.webdriver.remote.webdriver import WebDriver
from browser.element_helper import ElementHelper
from browser.screenshot import ScreenshotManager
from models.record import Record
from utils.logger import get_logger
from engine.field_detector import FieldDetector
from engine.form_filler import fill_form

log = get_logger(__name__)


class FormFiller:
    """
    Step 3 — Smart form filler using FieldDetector + DecisionEngine.
    Auto-detects all fields on page and fills them intelligently.

    Usage:
        form_filler = FormFiller(driver)
        success = form_filler.run(record)
    """

    # ── Submit button XPaths ───────────────────────────
    SUBMIT_XPATHS = [
        '//input[@name="btnSaveData"]',
        '//div[@id="btnSaveData_CD"]',
        '//input[@type="submit"]',
        '//button[contains(text(),"Submit")]',
        '//button[contains(text(),"Send")]',
        '//button[contains(text(),"submit")]',
        '//button[contains(text(),"Request")]',
        '//button[contains(text(),"Next")]',
        '//*[@id="submit"]',
        '//*[@id="submitBtn"]',
    ]

    # ── Success indicators ─────────────────────────────
    SUCCESS_INDICATORS = [
        '//*[contains(@class,"success")]',
        '//*[contains(@class,"confirmation")]',
        '//*[contains(@class,"thank")]',
        '//*[contains(text(),"Thank you")]',
        '//*[contains(text(),"successfully submitted")]',
        '//*[contains(text(),"received your request")]',
        '//*[contains(text(),"confirmation")]',
    ]

    def __init__(self, driver: WebDriver):
        self.driver     = driver
        self.helper     = ElementHelper(driver)
        self.screenshot = ScreenshotManager(driver)

    # ─────────────────────────────────────────────────
    # MAIN RUN
    # ─────────────────────────────────────────────────

    def run(self, record: Record) -> bool:
        """
        Smart form fill flow:
          1. Build row dict from record
          2. Auto-detect all fields on page
          3. Fill all fields using DecisionEngine + SemanticMatcher
          3.5 Solve captcha if present
          4. Submit form
          5. Verify submission
        """
        log.info(f"📝 [Row {record.row_number}] Starting smart form fill …")

        try:
            # ── Step 1: Build row dict ─────────────────
            row = {
                "Name"                 : f"{record.first_name or ''} {record.last_name or ''}".strip(),
                "Email"                : record.email,
                "Phone"                : record.phone or "",
                "Street Address"       : record.address,
                "City"                 : record.city,
                "State"                : record.state,
                "Zip"                  : record.zip_code,
                "Company"              : record.company or "",
                "Description"          : record.description,
                "Content Type"         : record.type_of_records,
                "records_requested_for": record.records_requested_for,
                "Department"           : record.department,
                "Domain"               : record.domain,
            }
            log.info(
                f"📋 [Row {record.row_number}] "
                f"Row dict built with {len(row)} fields"
            )

            # ── Step 2: Detect all fields on page ─────
            log.info(f"🔍 [Row {record.row_number}] Detecting form fields …")
            detector = FieldDetector(self.driver)
            form_map = detector.build_form_map()

            if not form_map:
                msg = "No form fields detected on page"
                log.error(f"❌ [Row {record.row_number}] {msg}")
                self.screenshot.capture(record.row_number, "no_fields_detected")
                record.mark_failed(msg)
                return False

            log.info(
                f"✅ [Row {record.row_number}] "
                f"Detected {len(form_map)} fields"
            )

            # ── Step 3: Fill all fields ────────────────
            fill_form(self.driver, row, form_map)
            log.info(f"✅ [Row {record.row_number}] All fields filled")
            time.sleep(1)

            # ── Step 3.5: Solve captcha ────────────────
            self._solve_captcha(record)
            time.sleep(1)

            # ── Step 4: Submit ─────────────────────────
            if not self._submit_form(record):
                return False

            # ── Step 5: Verify ─────────────────────────
            time.sleep(3)
            return self._verify_submission(record)

        except Exception as e:
            msg = f"Smart form fill failed → {e}"
            log.error(f"❌ [Row {record.row_number}] {msg}")
            screenshot_path = self.screenshot.capture(
                record.row_number, "form_fill_error"
            )
            record.mark_failed(msg, screenshot_path)
            return False

    # ─────────────────────────────────────────────────
    # SOLVE CAPTCHA
    # ─────────────────────────────────────────────────

    def _solve_captcha(self, record: Record) -> bool:
        """
        Solve captcha after form fields are filled.
        Uses CaptchaManager which tries:
          1. Image solver (OpenCV + Tesseract)
          2. Audio solver (Whisper) as fallback

        Returns:
            True if solved or no captcha found
            False if solving failed
        """
        log.info(
            f"🔐 [Row {record.row_number}] "
            f"Checking for captcha …"
        )
        try:
            from utils.captcha_manager import CaptchaManager
            captcha_manager = CaptchaManager(self.driver)
            solved          = captcha_manager.solve(record=record)

            if solved:
                log.info(
                    f"✅ [Row {record.row_number}] "
                    f"Captcha solved"
                )
            else:
                log.warning(
                    f"⚠️  [Row {record.row_number}] "
                    f"Captcha not solved — submitting anyway"
                )
            return solved

        except Exception as e:
            log.warning(
                f"⚠️  [Row {record.row_number}] "
                f"Captcha error → {e} — submitting anyway"
            )
            return False

    # ─────────────────────────────────────────────────
    # SUBMIT
    # ─────────────────────────────────────────────────

    def _submit_form(self, record: Record) -> bool:
        """Click the form submit button."""
        log.info(f"🚀 [Row {record.row_number}] Submitting form …")

        for xpath in self.SUBMIT_XPATHS:
            if self.helper.is_present(xpath):
                success = self.helper.click_xpath(xpath)
                if success:
                    log.info(
                        f"✅ [Row {record.row_number}] "
                        f"Form submitted via: {xpath[:60]}"
                    )
                    return True

        msg = "Could not find form submit button"
        log.error(f"❌ [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(
            record.row_number, "submit_button_not_found"
        )
        record.mark_failed(msg, screenshot_path)
        return False

    # ─────────────────────────────────────────────────
    # VERIFY
    # ─────────────────────────────────────────────────

    def _verify_submission(self, record: Record) -> bool:
        """Verify form submitted successfully + cleanup captcha temp files."""
        log.info(f"🔎 [Row {record.row_number}] Verifying submission …")

        # ── Check success indicators ───────────────────
        for xpath in self.SUCCESS_INDICATORS:
            if self.helper.is_present(xpath):
                text = self.helper.get_text(xpath) or "Success"
                log.info(
                    f"✅ [Row {record.row_number}] "
                    f"Confirmed: '{text[:60]}'"
                )
                self.screenshot.capture(
                    record.row_number,
                    "submitted_success",
                    is_error=False
                )
                record.mark_success()
                self._cleanup_captcha(record)
                return True

        # ── URL fallback ───────────────────────────────
        current_url = self.driver.current_url.lower()
        success_kws = ["submit", "confirm", "thank", "success", "complete"]

        if any(kw in current_url for kw in success_kws):
            log.info(
                f"✅ [Row {record.row_number}] "
                f"Confirmed via URL: {current_url[:60]}"
            )
            self.screenshot.capture(
                record.row_number,
                "submitted_url_confirm",
                is_error=False
            )
            record.mark_success()
            self._cleanup_captcha(record)
            return True

        # ── Could not confirm ──────────────────────────
        msg = "Submission unclear — no confirmation found"
        log.warning(f"⚠️  [Row {record.row_number}] {msg}")
        self.screenshot.capture(record.row_number, "submission_unclear")
        record.mark_failed(msg)
        return False

    # ─────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────

    def _cleanup_captcha(self, record: Record) -> None:
        """Clean up temp captcha images after successful submission."""
        try:
            from utils.captcha_image_solver import CaptchaImageSolver
            CaptchaImageSolver(self.driver).cleanup_temp(record)
            log.debug(
                f"🗑️  [Row {record.row_number}] "
                f"Captcha temp files cleaned"
            )
        except Exception:
            pass
# ```

# ---

# **What was fixed and why:**

# | Issue | Old code | Fixed |
# |---|---|---|
# | Unused import | `from utils.captcha_solver import CaptchaSolver` at top | Removed completely |
# | `_submit_form()` called twice | Two `if not self._submit_form()` blocks | Only one call now |
# | Dead commented code | Old `CaptchaImageSolver` block | Removed completely |
# | Captcha logic inline in `run()` | Mixed in with other code | Moved to `_solve_captcha()` method |
# | Cleanup duplicated | In two places in `_verify_submission()` | Moved to `_cleanup_captcha()` method |

# **Clean flow now:**
# ```
# run()
#   ↓ Step 1: Build row dict
#   ↓ Step 2: Detect fields
#   ↓ Step 3: Fill fields
#   ↓ Step 3.5: _solve_captcha()  ← CaptchaManager handles everything
#   ↓ Step 4: _submit_form()      ← called ONCE
#   ↓ Step 5: _verify_submission() + _cleanup_captcha()