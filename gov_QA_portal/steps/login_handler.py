import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from browser.element_helper import ElementHelper
from browser.screenshot import ScreenshotManager
from models.record import Record
from utils.logger import get_logger
from utils.retry import retry

log = get_logger(__name__)

class LoginHandler:
    """
    Step 2 — Fill in the login form with email and password
    from the record and complete the login process.

    Usage:
        login_handler = LoginHandler(driver)
        success = login_handler.run(record)
    """

    # ─────────────────────────────────────────────────
    # XPATHS — update these to match the actual site
    # ─────────────────────────────────────────────────

    EMAIL_XPATHS = [
        '//input[@aria-label="Email Address"]',
        '//input[@type="email"]',
        '//input[@name="email"]',
        '//input[@id="email"]',
        '//input[@name="username"]',
        '//input[@id="username"]',
        '//input[contains(@placeholder,"email") or contains(@placeholder,"Email")]',
        '//input[contains(@placeholder,"username") or contains(@placeholder,"Username")]',
    ]

    PASSWORD_XPATHS = [
        '//input[@aria-label="Password"]',
        '//input[@type="password"]',
        '//input[@name="password"]',
        '//input[@id="password"]',
        '//input[contains(@placeholder,"password") or contains(@placeholder,"Password")]',
    ]

    SUBMIT_XPATHS = [
        '//div[@id="RequesLoginFormLayout_btnLogin_CD"]',
        '//button[@type="submit"]',
        '//input[@type="submit"]',
        '//button[contains(translate(text(), "LOGIN", "login"), "login")]',
        '//button[contains(translate(text(), "SIGN", "sign"), "sign in")]',
        '//a[contains(translate(text(), "LOGIN", "login"), "login")]',
        '//*[@id="login-button"]',
        '//*[@id="submit"]',
    ]

    SUCCESS_INDICATORS = [
        '//span[contains(text(),"Logged in as")]',
        '//td[@id="captchaFormLayout_0"]',
        '//div[@id="applicationcontent"]//form',
    ]

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.helper = ElementHelper(driver)
        self.screenshot = ScreenshotManager(driver)

    # ─────────────────────────────────────────────────
    # MAIN RUN
    # ─────────────────────────────────────────────────

    def run(self, record: Record) -> bool:
        """
        Orchestrates the login flow: Email -> Password -> Captcha -> Submit -> Verify
        """
        log.info(f"🔄 [Row {record.row_number}] Starting login sequence...")

        # 1. Fill Email
        if not self._fill_email(record):
            return False
            
        # 2. Fill Password
        if not self._fill_password(record):
            return False

        # 3. Handle Captcha (Optional/If Present)
        # solver = CaptchaSolver(self.driver, domain=record.domain)
        # if not solver.solve():
        #     log.warning(
        #         f"⚠️  [Row {record.row_number}] "
        #         f"Captcha could not be solved — attempting to continue anyway."
        #     )

        # 4. Submit the Form
        if not self._submit_form(record):
            return False

        # Allow a brief moment for the page to transition before verifying
        time.sleep(3)

        # 5. Verify the Login was successful
        return self._verify_login(record)


    # ─────────────────────────────────────────────────
    # FILL EMAIL
    # ─────────────────────────────────────────────────

    @retry(max_attempts=3, delay=2, on_failure="skip")
    def _fill_email(self, record: Record) -> bool:
        log.info(f"📧 [Row {record.row_number}] Filling email field …")

        for xpath in self.EMAIL_XPATHS:
            if self.helper.is_present(xpath):
                success = self.helper.type_xpath(
                    xpath,
                    record.email,
                    clear_first=True
                )
                if success:
                    log.info(f"✅ [Row {record.row_number}] Email filled using: {xpath[:60]}")
                    return True

        msg = "Could not find email/username input field"
        log.error(f"❌ [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(record.row_number, "email_field_not_found")
        record.mark_failed(msg, screenshot_path)
        return False

    # ─────────────────────────────────────────────────
    # FILL PASSWORD
    # ─────────────────────────────────────────────────

    @retry(max_attempts=3, delay=2, on_failure="skip")
    def _fill_password(self, record: Record) -> bool:
        log.info(f"🔑 [Row {record.row_number}] Filling password field …")

        for xpath in self.PASSWORD_XPATHS:
            if self.helper.is_present(xpath):
                success = self.helper.type_xpath(
                    xpath,
                    record.password,
                    clear_first=True
                )
                if success:
                    log.info(f"✅ [Row {record.row_number}] Password filled using: {xpath[:60]}")
                    return True

        msg = "Could not find password input field"
        log.error(f"❌ [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(record.row_number, "password_field_not_found")
        record.mark_failed(msg, screenshot_path)
        return False

    # ─────────────────────────────────────────────────
    # SUBMIT FORM
    # ─────────────────────────────────────────────────

    @retry(max_attempts=3, delay=2, on_failure="skip")
    def _submit_form(self, record: Record) -> bool:
        log.info(f"🚀 [Row {record.row_number}] Submitting login form …")

        # ── Strategy 1: Click submit button ───────────
        for xpath in self.SUBMIT_XPATHS:
            if self.helper.is_present(xpath):
                success = self.helper.click_xpath(xpath)
                if success:
                    log.info(f"✅ [Row {record.row_number}] Submit clicked using: {xpath[:60]}")
                    return True

        # ── Strategy 2: Press ENTER on password field ──
        log.warning(f"⚠️  [Row {record.row_number}] No submit button found, trying ENTER key …")
        
        for xpath in self.PASSWORD_XPATHS:
            if self.helper.is_present(xpath):
                try:
                    element = self.driver.find_element("xpath", xpath)
                    element.send_keys(Keys.RETURN)
                    log.info(f"✅ [Row {record.row_number}] Submitted via ENTER key")
                    return True
                except Exception:
                    continue

        msg = "Could not find or click login submit button"
        log.error(f"❌ [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(record.row_number, "submit_button_not_found")
        record.mark_failed(msg, screenshot_path)
        return False

    # ─────────────────────────────────────────────────
    # VERIFY LOGIN
    # ─────────────────────────────────────────────────

    def _verify_login(self, record: Record) -> bool:
        log.info(f"🔎 [Row {record.row_number}] Verifying login …")

        # ── Check for success indicators ───────────────
        for xpath in self.SUCCESS_INDICATORS:
            if self.helper.is_present(xpath):
                log.info(f"✅ [Row {record.row_number}] Login verified — success indicator found")
                return True
        
        # ── Fallback: URL changed from login page ──────
        current_url = self.driver.current_url.lower()
        login_keywords = ["login", "signin", "sign-in", "auth"]

        if not any(kw in current_url for kw in login_keywords):
            log.info(f"✅ [Row {record.row_number}] Login assumed success — URL no longer on login page: {current_url[:60]}")
            return True

        # ── Could not confirm success ───────────────────
        msg = "Login status unclear — still on login page with no error shown"
        log.warning(f"⚠️  [Row {record.row_number}] {msg}")
        screenshot_path = self.screenshot.capture(record.row_number, "login_unclear")
        record.mark_failed(msg, screenshot_path)
        return False