import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from config.settings import (
    HEADLESS,
    PAGE_LOAD_TIMEOUT,
    SCREENSHOT_DIR,
)
from utils.logger import get_logger

log = get_logger(__name__)


class DriverSetup:
    """
    Initializes and manages the Selenium WebDriver.

    Usage:
        driver_setup = DriverSetup()
        driver       = driver_setup.get_driver()
        ...
        driver_setup.quit()
    """

    def __init__(self):
        self.driver = None
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ─────────────────────────────────────────────────
    # GET DRIVER
    # ─────────────────────────────────────────────────

    def get_driver(self):                            # ✅ Fixed — added 'self'
        options = Options()
        prefs = {
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False
}

        if HEADLESS:
            options.add_argument("--headless=new")
            log.info("🖥️  Running in HEADLESS mode")
        else:
            log.info("🖥️  Running in VISIBLE mode")

        # ── Stability options ──────────────────────────
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # ── Anti bot detection ─────────────────────────
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        # service     = ChromeService(ChromeDriverManager().install())
        # self.driver = webdriver.Chrome(service=service, options=options)
        self.driver = webdriver.Chrome(options=options)

        # ── Remove webdriver flag ──────────────────────
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(5)

        log.info("✅ WebDriver initialized successfully")
        return self.driver

    # ─────────────────────────────────────────────────
    # OPEN PORTAL
    # ─────────────────────────────────────────────────

    def open_portal(self, url: str, timeout: int = 30):
        """
        Open the portal URL and handle:
          - Continue button if present
          - Form visibility wait
          - Popup close if present
        """
        wait = WebDriverWait(self.driver, timeout)

        log.info(f"🌐 Opening portal: {url}")
        self.driver.get(url)

        try:
            # ── Wait for form OR continue button ──────
            wait.until(
                EC.any_of(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@id="formWrap"]//input[@type="text"]')
                    ),
                    EC.presence_of_element_located(
                        (By.XPATH, "//span[normalize-space()='Continue']")
                    )
                )
            )
            log.info("🔍 Page loaded, checking flow …")

            # ── Click Continue if present ──────────────
            try:
                continue_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//span[normalize-space()='Continue']")
                    )
                )
                self.driver.execute_script(
                    "arguments[0].click();", continue_btn
                )
                log.info("✅ Clicked Continue button")

            except TimeoutException:
                log.info("✅ Form loaded directly — no Continue button")

            # ── Wait for form input to be visible ──────
            try:
                wait.until(
                    EC.visibility_of_element_located(
                        (By.XPATH, '//div[@id="formWrap"]//input[@type="text"]')
                    )
                )
            except TimeoutException:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//div[@id="formWrap"]//input[@type="text"]')
                    )
                )

            log.info("✅ Form is visible and ready")

            # ── Close popup if present ─────────────────
            try:
                close_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//div[@role="dialog"]//button[contains(@class,"cp-Splash-Btn--Close")]')
                    )
                )
                close_btn.click()
                log.info("✅ Popup closed")

            except TimeoutException:
                pass  # No popup — that's fine

        except TimeoutException:
            raise Exception(
                f"❌ Portal opened but form not detected at: {url}"
            )

    # ─────────────────────────────────────────────────
    # QUIT
    # ─────────────────────────────────────────────────

    def quit(self):
        """Safely close and quit the WebDriver session."""
        if self.driver:
            try:
                self.driver.quit()
                log.info("🔒 WebDriver session closed")
            except Exception as e:
                log.warning(f"⚠️  Error closing WebDriver → {e}")
            finally:
                self.driver = None

    # ─────────────────────────────────────────────────
    # CONTEXT MANAGER
    # ─────────────────────────────────────────────────

    def __enter__(self):
        return self.get_driver()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()