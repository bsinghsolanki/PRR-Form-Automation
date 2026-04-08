from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.normalizer import normalize


# CSS selectors for CivicPlus and standard NJ form field containers.
_FIELD_CONTAINER_CSS = (
    "ol.selfClear.cpForm > li, "
    "li.form-li, "
    "div.form-group, "
    "div.field-wrapper"
)

_LABEL_CSS = "label.field-label, legend, span.label-text, strong, label"


def build_form_map(driver: WebDriver) -> dict:
    """
    Scan the current page for form fields and return a structured map.

    Returns:
        {
          "<normalised label>": {
              "type":     str,            # "text" | "textarea" | "dropdown" |
                                          #  "radio" | "checkbox" | "date"
              "element":  WebElement | list[WebElement],
              "required": bool,
              "full_text": str,           # raw container text (useful for debugging)
          },
          ...
        }
    """
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "form"))
    )

    containers = driver.find_elements(By.CSS_SELECTOR, _FIELD_CONTAINER_CSS)
    form_map: dict = {}

    for container in containers:
        try:
            label, meta = _parse_field(driver, container)
            if label and meta:
                form_map[label] = meta
        except Exception as exc:
            print(f"[field_detector] Skipping field: {exc}")

    return form_map


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _parse_field(driver, container) -> tuple[str | None, dict | None]:
    """Extract label and field metadata from a single container element."""
    label_els = container.find_elements(By.CSS_SELECTOR, _LABEL_CSS)
    if not label_els:
        return None, None

    label = normalize(label_els[0].text)
    if not label:
        return None, None

    is_required = "*" in label_els[0].text or "required" in container.text.lower()

    f_type, element = _detect_input(container)
    if not (f_type and element):
        return None, None

    return label, {
        "type":      f_type,
        "element":   element,
        "required":  is_required,
        "full_text": normalize(container.text),
    }


def _detect_input(container):
    """Return (field_type, element_or_list) for the first input found in *container*."""
    # Check in specificity order: most specific → most general.
    if textareas := container.find_elements(By.TAG_NAME, "textarea"):
        return "textarea", textareas[0]

    if selects := container.find_elements(By.TAG_NAME, "select"):
        return "dropdown", selects[0]

    if radios := container.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
        return "radio", radios

    if checkboxes := container.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
        return "checkbox", checkboxes

    inputs = container.find_elements(
        By.CSS_SELECTOR,
        "input[type='text'], input[type='email'], input[type='tel'], input[type='date']",
    )
    if inputs:
        inp = inputs[0]
        is_date = inp.get_attribute("type") == "date"
        return ("date" if is_date else "text"), inp

    return None, None
