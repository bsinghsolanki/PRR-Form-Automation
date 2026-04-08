import time
from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    NoSuchElementException,
    ElementNotInteractableException,
)
from config.settings import ELEMENT_WAIT_TIMEOUT
from utils.logger import get_logger

log = get_logger(__name__)


class ElementHelper:
    """
    All Selenium interactions go through this class.
    Provides safe, logged, retry-aware wrappers for
    finding, clicking, typing, and selecting elements.

    Usage:
        helper = ElementHelper(driver)
        helper.click_xpath('//button[@id="submit"]')
        helper.type_xpath('//input[@name="email"]', "user@mail.com")
    """

    def __init__(self, driver: WebDriver, timeout: int = ELEMENT_WAIT_TIMEOUT):
        self.driver  = driver
        self.timeout = timeout
        self.wait    = WebDriverWait(driver, timeout)
        self.actions = ActionChains(driver)

    # ─────────────────────────────────────────────────
    # WAIT & FIND
    # ─────────────────────────────────────────────────

    def wait_for_element(
        self,
        xpath: str,
        timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """Wait until element is present in DOM and return it."""
        t = timeout or self.timeout
        try:
            element = WebDriverWait(self.driver, t).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            log.debug(f"✅ Element found: {xpath[:80]}")
            return element
        except TimeoutException:
            log.warning(f"⚠️  Element not found after {t}s: {xpath[:80]}")
            return None

    def wait_for_clickable(
        self,
        xpath: str,
        timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """Wait until element is visible AND clickable."""
        t = timeout or self.timeout
        try:
            element = WebDriverWait(self.driver, t).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            log.debug(f"✅ Element clickable: {xpath[:80]}")
            return element
        except TimeoutException:
            log.warning(f"⚠️  Element not clickable after {t}s: {xpath[:80]}")
            return None

    def wait_for_visible(
        self,
        xpath: str,
        timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """Wait until element is visible on screen."""
        t = timeout or self.timeout
        try:
            element = WebDriverWait(self.driver, t).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
            log.debug(f"✅ Element visible: {xpath[:80]}")
            return element
        except TimeoutException:
            log.warning(f"⚠️  Element not visible after {t}s: {xpath[:80]}")
            return None

    def find_all(self, xpath: str) -> List[WebElement]:
        """Return all matching elements (empty list if none found)."""
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)
            log.debug(f"🔍 Found {len(elements)} elements: {xpath[:80]}")
            return elements
        except Exception as e:
            log.warning(f"⚠️  find_all failed → {e}")
            return []

    # ─────────────────────────────────────────────────
    # CLICK
    # ─────────────────────────────────────────────────

    def click_xpath(self, xpath: str, use_js: bool = False) -> bool:
        """
        Click an element by XPath.
        Falls back to JavaScript click if normal click is intercepted.

        Args:
            xpath   : XPath of element to click
            use_js  : Force JavaScript click (bypasses overlays)

        Returns:
            True if click succeeded, False otherwise
        """
        try:
            element = self.wait_for_clickable(xpath)
            if not element:
                return False

            self._scroll_to(element)

            if use_js:
                self.driver.execute_script("arguments[0].click();", element)
                log.info(f"🖱️  JS clicked: {xpath[:80]}")
            else:
                element.click()
                log.info(f"🖱️  Clicked: {xpath[:80]}")

            return True

        except ElementClickInterceptedException:
            log.warning(f"⚠️  Click intercepted, retrying with JS: {xpath[:80]}")
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script("arguments[0].click();", element)
                log.info(f"🖱️  JS fallback click succeeded: {xpath[:80]}")
                return True
            except Exception as e:
                log.error(f"❌ JS fallback click failed → {e}")
                return False

        except StaleElementReferenceException:
            log.warning(f"⚠️  Stale element, retrying: {xpath[:80]}")
            time.sleep(1)
            return self.click_xpath(xpath, use_js)

        except Exception as e:
            log.error(f"❌ Click failed on {xpath[:80]} → {e}")
            return False

    # ─────────────────────────────────────────────────
    # TYPE / INPUT
    # ─────────────────────────────────────────────────

    def type_xpath(
        self,
        xpath: str,
        text: str,
        clear_first: bool = True,
        slow: bool = False
    ) -> bool:
        """
        Type text into an input field.

        Args:
            xpath       : XPath of the input element
            text        : Text to type
            clear_first : Clear existing value before typing
            slow        : Type character by character (mimics human typing)

        Returns:
            True if typing succeeded, False otherwise
        """
        try:
            element = self.wait_for_element(xpath)
            if not element:
                return False

            self._scroll_to(element)

            if clear_first:
                element.clear()
                # JS clear as backup (some fields resist .clear())
                self.driver.execute_script("arguments[0].value = '';", element)

            if slow:
                for char in text:
                    element.send_keys(char)
                    time.sleep(0.05)
            else:
                element.send_keys(text)

            log.info(f"⌨️  Typed into {xpath[:60]} → '{text[:30]}{'…' if len(text)>30 else ''}'")
            return True

        except ElementNotInteractableException:
            log.warning(f"⚠️  Element not interactable, trying JS: {xpath[:80]}")
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                self.driver.execute_script(
                    f"arguments[0].value = '{text}';", element
                )
                return True
            except Exception as e:
                log.error(f"❌ JS type failed → {e}")
                return False

        except Exception as e:
            log.error(f"❌ Type failed on {xpath[:80]} → {e}")
            return False

    # ─────────────────────────────────────────────────
    # SELECT DROPDOWN
    # ─────────────────────────────────────────────────

    def select_by_visible_text(self, xpath: str, text: str) -> bool:
        """Select a <select> dropdown option by its visible text."""
        try:
            element = self.wait_for_element(xpath)
            if not element:
                return False
            Select(element).select_by_visible_text(text)
            log.info(f"📋 Selected '{text}' in dropdown: {xpath[:60]}")
            return True
        except Exception as e:
            log.error(f"❌ Select by text failed → {e}")
            return False

    def select_by_value(self, xpath: str, value: str) -> bool:
        """Select a <select> dropdown option by its value attribute."""
        try:
            element = self.wait_for_element(xpath)
            if not element:
                return False
            Select(element).select_by_value(value)
            log.info(f"📋 Selected value='{value}' in: {xpath[:60]}")
            return True
        except Exception as e:
            log.error(f"❌ Select by value failed → {e}")
            return False

    # ─────────────────────────────────────────────────
    # CHECKBOX & RADIO
    # ─────────────────────────────────────────────────

    def check_checkbox(self, xpath: str, should_check: bool = True) -> bool:
        """
        Check or uncheck a checkbox.

        Args:
            xpath        : XPath of the checkbox
            should_check : True to check, False to uncheck
        """
        try:
            element = self.wait_for_element(xpath)
            if not element:
                return False

            is_checked = element.is_selected()

            if should_check and not is_checked:
                self.click_xpath(xpath)
                log.info(f"☑️  Checkbox checked: {xpath[:60]}")
            elif not should_check and is_checked:
                self.click_xpath(xpath)
                log.info(f"⬜ Checkbox unchecked: {xpath[:60]}")
            else:
                log.debug(f"☑️  Checkbox already in desired state: {xpath[:60]}")

            return True
        except Exception as e:
            log.error(f"❌ Checkbox action failed → {e}")
            return False

    def click_radio(self, xpath: str) -> bool:
        """Click a radio button."""
        return self.click_xpath(xpath)

    # ─────────────────────────────────────────────────
    # PAGE HELPERS
    # ─────────────────────────────────────────────────

    def wait_for_page_load(self, timeout: int = 30) -> bool:
        """Wait until document.readyState is 'complete'."""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            log.debug("✅ Page fully loaded")
            return True
        except TimeoutException:
            log.warning("⚠️  Page load timeout")
            return False

    def wait_for_url_contains(self, partial_url: str, timeout: int = 15) -> bool:
        """Wait until the current URL contains a specific string."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.url_contains(partial_url)
            )
            log.info(f"✅ URL now contains: '{partial_url}'")
            return True
        except TimeoutException:
            log.warning(f"⚠️  URL did not contain '{partial_url}' after {timeout}s")
            return False

    def get_text(self, xpath: str) -> Optional[str]:
        """Return the text content of an element, or None if not found."""
        element = self.wait_for_element(xpath)
        if element:
            return element.text.strip()
        return None

    def is_present(self, xpath: str) -> bool:
        """Return True if element exists in DOM (no waiting)."""
        return len(self.driver.find_elements(By.XPATH, xpath)) > 0

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)

    # ─────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────

    def _scroll_to(self, element: WebElement):
        """Scroll element into view before interacting."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", element
            )
            time.sleep(0.3)
        except Exception:
            pass