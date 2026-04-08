import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from utils.normalizer import normalize
from utils.logger import get_logger

log = get_logger(__name__)


class FieldDetector:
    """
    Scans the page and builds a form_map of all detected fields.

    form_map structure:
    {
        "field label" : {
            "type"     : "text" | "textarea" | "dropdown" |
                         "radio" | "checkbox" | "date",
            "element"  : WebElement or List[WebElement],
            "required" : True | False,
        }
    }

    Usage:
        detector = FieldDetector(driver)
        form_map = detector.build_form_map()
    """

    def __init__(self, driver: WebDriver, timeout: int = 15):
        self.driver  = driver
        self.wait    = WebDriverWait(driver, timeout)

    def build_form_map(self) -> dict:
        """
        Scan entire page for form fields and return form_map.

        Returns:
            dict of {label: {type, element, required}}
        """
        form_map = {}
        log.info("🔍 Scanning page for form fields …")

        # ── Text inputs ──────────────────────────────────
        self._detect_text_inputs(form_map)

        # ── Textareas ────────────────────────────────────
        self._detect_textareas(form_map)

        # ── Dropdowns ────────────────────────────────────
        self._detect_dropdowns(form_map)

        # ── Radio buttons ────────────────────────────────
        self._detect_radios(form_map)

        # ── Checkboxes ───────────────────────────────────
        self._detect_checkboxes(form_map)

        # ── Date inputs ──────────────────────────────────
        self._detect_dates(form_map)

        log.info(f"✅ Detected {len(form_map)} fields total")
        return form_map

    # ─────────────────────────────────────────────────
    # DETECTORS
    # ─────────────────────────────────────────────────

    def _detect_text_inputs(self, form_map: dict) -> None:
        inputs = self.driver.find_elements(
            By.XPATH,
            '//input[@type="text" or @type="email" or '
            '@type="tel" or @type="number" or not(@type)]'
        )
        for el in inputs:
            label    = self._get_label(el)
            required = self._is_required(el)
            if label:
                form_map[label] = {
                    "type"    : "text",
                    "element" : el,
                    "required": required,
                }
                log.debug(f"  📝 text: '{label}' required={required}")

    def _detect_textareas(self, form_map: dict) -> None:
        areas = self.driver.find_elements(By.TAG_NAME, "textarea")
        for el in areas:
            label    = self._get_label(el)
            required = self._is_required(el)
            if label:
                form_map[label] = {
                    "type"    : "textarea",
                    "element" : el,
                    "required": required,
                }
                log.debug(f"  📄 textarea: '{label}' required={required}")

    def _detect_dropdowns(self, form_map: dict) -> None:
        selects = self.driver.find_elements(By.TAG_NAME, "select")
        for el in selects:
            label    = self._get_label(el)
            required = self._is_required(el)
            if label:
                form_map[label] = {
                    "type"    : "dropdown",
                    "element" : el,
                    "required": required,
                }
                log.debug(f"  📋 dropdown: '{label}' required={required}")

    def _detect_radios(self, form_map: dict) -> None:
        radios = self.driver.find_elements(
            By.XPATH, '//span[@role="radio"] | //input[@type="radio"]'
        )
        groups = {}
        for el in radios:
            name = el.get_attribute("name") or self._get_label(el)
            if name:
                groups.setdefault(name, []).append(el)

        for group_name, elements in groups.items():
            label    = self._get_group_label(group_name, elements)
            required = self._is_required(elements[0])
            form_map[label] = {
                "type"    : "radio",
                "element" : elements,
                "required": required,
            }
            log.debug(f"  🔘 radio: '{label}' ({len(elements)} options)")

    def _detect_checkboxes(self, form_map: dict) -> None:
        checkboxes = self.driver.find_elements(
            By.XPATH, '//input[@type="checkbox"]'
        )
        groups = {}
        for el in checkboxes:
            name = el.get_attribute("name") or self._get_label(el)
            if name:
                groups.setdefault(name, []).append(el)

        for group_name, elements in groups.items():
            label    = self._get_group_label(group_name, elements)
            required = self._is_required(elements[0])
            form_map[label] = {
                "type"    : "checkbox",
                "element" : elements,
                "required": required,
            }
            log.debug(f"  ☑️  checkbox: '{label}' ({len(elements)} options)")

    def _detect_dates(self, form_map: dict) -> None:
        dates = self.driver.find_elements(
            By.XPATH, '//input[@type="date"]'
        )
        for el in dates:
            label    = self._get_label(el)
            required = self._is_required(el)
            if label:
                form_map[label] = {
                    "type"    : "date",
                    "element" : el,
                    "required": required,
                }
                log.debug(f"  📅 date: '{label}' required={required}")

    # ─────────────────────────────────────────────────
    # LABEL HELPERS
    # ─────────────────────────────────────────────────

    def _get_label(self, element) -> str:
        """
        Try multiple strategies to find the label for an element.
        Returns empty string if none found.
        """
        # Strategy 1: <label for="id">
        try:
            el_id = element.get_attribute("id")
            if el_id:
                lbl = self.driver.find_element(
                    By.XPATH, f"//label[@for='{el_id}']"
                )
                text = lbl.text.strip()
                if text:
                    return text
        except Exception:
            pass

        # Strategy 2: aria-label attribute
        aria = element.get_attribute("aria-label")
        if aria and aria.strip():
            return aria.strip()

        # Strategy 3: placeholder attribute
        placeholder = element.get_attribute("placeholder")
        if placeholder and placeholder.strip():
            return placeholder.strip()

        # Strategy 4: name attribute
        name = element.get_attribute("name")
        if name and name.strip():
            return name.strip().replace("_", " ").replace("-", " ")

        # Strategy 5: parent/sibling text
        try:
            parent_text = element.find_element(
                By.XPATH, ".."
            ).text.strip()
            if parent_text:
                return parent_text.split("\n")[0]
        except Exception:
            pass

        return ""

    def _get_group_label(self, group_name: str, elements: list) -> str:
        """Get label for a radio/checkbox group."""
        # Try label of first element
        label = self._get_label(elements[0])
        if label:
            return label

        # Fallback to group name (the 'name' attribute)
        return group_name.replace("_", " ").replace("-", " ")

    def _is_required(self, element) -> bool:
        """Check if field is marked as required."""
        try:
            required_attr = element.get_attribute("required")
            aria_required = element.get_attribute("aria-required")
            return (
                required_attr is not None and required_attr != "false"
            ) or (
                aria_required == "true"
            )
        except Exception:
            return False