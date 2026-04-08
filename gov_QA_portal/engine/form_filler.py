"""
engine/form_filler.py
=====================
Single entry point: fill_form(driver, row, form_map)

Resolution order for every field:
  1. DecisionEngine  — dates, delivery, acknowledgment, department
  2. FIELD_MAP       — static keyword → sheet column mapping
  3. SemanticMatcher — fuzzy/synonym fallback
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException

from engine.decision_engine import DecisionEngine
from engine.semantic_matcher import SemanticMatcher
from utils.constants import FIELD_MAP
from utils.normalizer import normalize
from utils.logger import get_logger

log = get_logger(__name__)


# ─────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────

def fill_form(driver: WebDriver, row: dict, form_map: dict) -> None:
    """
    Fill every field in form_map using data from row dict.

    Args:
        driver   : Active Selenium WebDriver
        row      : {column_name: value} dict built from Record
        form_map : Output of FieldDetector.build_form_map()
    """
    from datetime import datetime
    today   = datetime.now().strftime("%m/%d/%Y")
    engine  = DecisionEngine()
    matcher = SemanticMatcher(list(row.keys()))

    log.info(f"🧠 Fields to fill: {len(form_map)}")
    log.info(f"🔑 Row keys: {list(row.keys())}")

    for label, meta in form_map.items():
        try:
            _fill_field(driver, row, label, meta, engine, matcher, today)
        except StaleElementReferenceException:
            log.warning(f"⚠️  Stale element skipped: '{label}'")
        except Exception as e:
            log.warning(f"⚠️  Failed to fill '{label}' → {e}")


# ─────────────────────────────────────────────────────
# PER FIELD ORCHESTRATION
# ─────────────────────────────────────────────────────

def _fill_field(
    driver  : WebDriver,
    row     : dict,
    label   : str,
    meta    : dict,
    engine  : DecisionEngine,
    matcher : SemanticMatcher,
    today   : str,
) -> None:
    l        = normalize(label)
    f_type   = meta["type"]
    element  = meta["element"]
    required = meta["required"]

    # Scroll element into view
    _scroll_to(driver, element)

    # Get visible options for select/radio/checkbox
    options = _get_options(driver, f_type, element)

    # ── Step 1: DecisionEngine ────────────────────────
    description = row.get("Description", "")
    decision    = engine.decide(l, f_type, options, description)

    if decision == "__SKIP__":
        log.debug(f"⏭️  Skipped: '{label}'")
        return

    if decision is not None:
        _apply_decision(driver, row, decision, f_type, element, options, today)
        return

    # ── Step 2: FIELD_MAP keyword lookup ──────────────
    sheet_col = _resolve_column(l, matcher)

    if not sheet_col:
        if required:
            log.warning(f"🚨 Required field has no mapping: '{label}'")
        return

    # ── Department special handling ───────────────────
    if sheet_col == "Department" and f_type in ("dropdown", "radio", "checkbox"):
        if _handle_department(driver, f_type, element, engine):
            return

    # ── Get value from row ────────────────────────────
    value = _get_row_value(row, sheet_col)

    if not value:
        if required:
            log.warning(f"🚨 Required value missing for: '{sheet_col}'")
        return

    # ── Email textbox special handling ────────────────
    if sheet_col.lower() == "email":
        _fill_email_textbox(driver, str(value))
        return

    # ── Step 3: Fill by type ──────────────────────────
    _fill_by_type(driver, f_type, element, str(value))
    log.info(f"✅ Filled '{label}' ← '{sheet_col}' = {str(value)[:40]!r}")


# ─────────────────────────────────────────────────────
# DECISION APPLICATION
# ─────────────────────────────────────────────────────

def _apply_decision(
    driver   : WebDriver,
    row      : dict,
    decision : str,
    f_type   : str,
    element,
    options  : list,
    today    : str,
) -> None:
    """Translate a DecisionEngine token into a Selenium action."""

    # ── Date ──────────────────────────────────────────
    if decision == "__TODAY__" or (
        len(decision) == 10 and decision.count("/") == 2
    ):
        target = element if not isinstance(element, list) else element[0]
        try:
            driver.execute_script(
                "arguments[0].value = arguments[1];", target, decision
            )
            log.info(f"✅ Date set → {decision}")
        except Exception:
            target.clear()
            target.send_keys(decision)
        return

    # ── Signature ─────────────────────────────────────
    if decision == "__SIGN__":
        name = _get_row_value(row, "Name")
        if name and f_type in ("text", "textarea"):
            element.clear()
            element.send_keys(name)
            log.info(f"✅ Signature filled: {name}")
        return

    # ── Description ───────────────────────────────────
    if decision == "__DESCRIPTION__":
        desc = _get_row_value(row, "Description")
        if desc and f_type in ("text", "textarea"):
            element.clear()
            element.send_keys(desc)
            log.info("✅ Description filled")
        return

    # ── Checkbox check ────────────────────────────────
    if decision == "__CHECK__":
        targets = element if isinstance(element, list) else [element]
        for el in targets:
            if not el.is_selected():
                driver.execute_script("arguments[0].click();", el)
            try:
                if not el.is_selected():
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(0.2)
                    log.info("☑️  Checkbox checked")
            except Exception as e:
                log.warning(f"⚠️  Could not check checkbox → {e}")
        log.info("✅ Checkbox(es) checked")
        return

    # ── NJ OPRA negatives ─────────────────────────────
    if decision == "__NJ_OPRA_NEG__":
        _click_nj_opra_negatives(driver, element)
        return

    # ── Single checkbox (email copy etc) ─────────────
    if f_type == "checkbox" and isinstance(element, list) and len(element) == 1:
        if not element[0].is_selected():
            driver.execute_script("arguments[0].click();", element[0])
        log.info("✅ Single checkbox clicked")
        return

    # ── Generic option string ─────────────────────────
    if f_type in ("radio", "checkbox"):
        _click_matching_option(driver, element, decision)
    elif f_type == "dropdown":
        _select_dropdown(element, decision)
    elif f_type in ("text", "textarea"):
        element.clear()
        element.send_keys(decision)
        log.info(f"✅ Text set: {decision!r}")


# ─────────────────────────────────────────────────────
# DEPARTMENT HANDLER
# ─────────────────────────────────────────────────────

def _handle_department(
    driver          : WebDriver,
    field_type      : str,
    element,
    decision_engine : DecisionEngine,
) -> bool:
    """
    Select best department using DEPARTMENT_PRIORITY.
    Handles dropdown, radio, and checkbox.
    """

    # ── Dropdown ──────────────────────────────────────
    if field_type == "dropdown":
        sel       = Select(element)
        available = [o.text.strip() for o in sel.options if o.text.strip()]
        best      = decision_engine.pick_department(available)

        if best:
            sel.select_by_visible_text(best)
            log.info(f"🏢 Department dropdown → '{best}'")
        else:
            sel.select_by_index(1)
            log.info("🏢 Department dropdown → fallback index 1")
        return True

    # ── Radio ─────────────────────────────────────────
    if field_type == "radio":
        available_map = _build_option_map(driver, element)
        best          = decision_engine.pick_department(list(available_map.keys()))

        if best and best in available_map:
            opt_el = available_map[best]
            if not opt_el.is_selected():
                driver.execute_script("arguments[0].click();", opt_el)
            log.info(f"🏢 Department radio → '{best}'")
            return True

    # ── Checkbox ──────────────────────────────────────
    if field_type == "checkbox":
        available_map = _build_option_map(driver, element)
        best          = decision_engine.pick_department(list(available_map.keys()))

        if best and best in available_map:
            opt_el = available_map[best]
            if not opt_el.is_selected():
                driver.execute_script("arguments[0].click();", opt_el)
            log.info(f"🏢 Department checkbox → '{best}'")
            return True

    return False


# ─────────────────────────────────────────────────────
# NJ OPRA HANDLER
# ─────────────────────────────────────────────────────

def _click_nj_opra_negatives(driver: WebDriver, elements) -> None:
    """Click every negative certification option (HAVE NOT / WILL NOT / AM NOT)."""
    neg_targets = ["have not", "will not", "am not", "i am not"]
    clicked     = 0

    for opt in (elements if isinstance(elements, list) else [elements]):
        lbl = _get_option_label(driver, opt)
        if any(t in lbl for t in neg_targets):
            if not opt.is_selected():
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.3)
            clicked += 1

    log.info(f"✅ NJ OPRA: clicked {clicked} negative certification(s)")


# ─────────────────────────────────────────────────────
# FIELD TYPE FILL HELPERS
# ─────────────────────────────────────────────────────

def _fill_by_type(
    driver  : WebDriver,
    f_type  : str,
    element,
    value   : str,
) -> None:
    """Fill a field based on its type."""
    if f_type in ("text", "textarea"):
        element.clear()
        element.send_keys(value)
    elif f_type == "date":
        try:
            driver.execute_script(
                "arguments[0].value = arguments[1];", element, value
            )
        except Exception:
            element.clear()
            element.send_keys(value)
    elif f_type == "dropdown":
        _select_dropdown(element, value)
    elif f_type in ("radio", "checkbox"):
        _click_matching_option(driver, element, value)


def _select_dropdown(element, target_text: str) -> None:
    """Select dropdown option by visible text (partial match)."""
    sel          = Select(element)
    target_lower = target_text.lower()

    # Try partial text match
    for opt in sel.options:
        if target_lower in opt.text.lower():
            sel.select_by_visible_text(opt.text)
            log.info(f"✅ Dropdown → '{opt.text}'")
            return

    # Fallback to first real option
    if len(sel.options) > 1:
        sel.select_by_index(1)
        log.warning("⚠️  Dropdown fallback → index 1")
    elif sel.options:
        sel.select_by_index(0)


def _click_matching_option(
    driver      : WebDriver,
    elements,
    target_text : str,
) -> None:
    """Click radio/checkbox option matching target text."""
    target_lower = target_text.lower()

    for opt in (elements if isinstance(elements, list) else [elements]):
        lbl = _get_option_label(driver, opt)
        if target_lower in lbl:
            if not opt.is_selected():
                driver.execute_script("arguments[0].click();", opt)
                log.info(f"✅ Selected option: '{lbl}'")
            return


def _fill_email_textbox(driver: WebDriver, value: str) -> None:
    """Special handler for email address textbox fields."""
    try:
        el = driver.find_element(
            By.XPATH,
            "//li//label[contains(text(),'Email Address')]"
            "/../div/input[@type='text']"
        )
        el.send_keys(value)
        log.info(f"✅ Email textbox filled: {value}")
    except Exception:
        log.debug("ℹ️  No special email textbox found")


# ─────────────────────────────────────────────────────
# OPTION / COLUMN HELPERS
# ─────────────────────────────────────────────────────

def _get_options(driver: WebDriver, f_type: str, element) -> list:
    """Get visible option texts for select/radio/checkbox fields."""
    if f_type == "dropdown":
        try:
            return [
                o.text.strip()
                for o in Select(element).options
                if o.text.strip()
            ]
        except Exception:
            return []

    if f_type in ("radio", "checkbox"):
        labels = []
        for opt in (element if isinstance(element, list) else [element]):
            text = _get_option_label(driver, opt)
            if text:
                labels.append(text)
        return labels

    return []


def _get_option_label(driver: WebDriver, opt_element) -> str:
    """Get visible label text for a radio/checkbox input."""
    # Try label[@for="id"]
    try:
        opt_id = opt_element.get_attribute("id")
        if opt_id:
            lbl = driver.find_element(By.XPATH, f"//label[@for='{opt_id}']")
            return lbl.text.lower().strip()
    except Exception:
        pass

    # Try aria-label or value attribute
    for attr in ("aria-label", "value"):
        val = opt_element.get_attribute(attr)
        if val:
            return val.lower().strip()

    # Try parent text
    try:
        return opt_element.find_element(By.XPATH, "..").text.lower().strip()
    except Exception:
        return ""


def _build_option_map(driver: WebDriver, elements) -> dict:
    """Build {label_text: element} map for radio/checkbox groups."""
    option_map = {}
    for opt in (elements if isinstance(elements, list) else [elements]):
        try:
            opt_id  = opt.get_attribute("id")
            lbl_txt = driver.find_element(
                By.XPATH, f"//label[@for='{opt_id}']"
            ).text.strip()
        except Exception:
            lbl_txt = (opt.get_attribute("value") or "").strip()
        if lbl_txt:
            option_map[lbl_txt] = opt
    return option_map


def _resolve_column(label: str, matcher: SemanticMatcher) -> str | None:
    """Resolve field label to sheet column via FIELD_MAP then SemanticMatcher."""
    for keyword, column in FIELD_MAP.items():
        if keyword in label:
            return column
    return matcher.match(label)


def _get_row_value(row: dict, target_col: str) -> str | None:
    """Case/whitespace insensitive row value accessor."""
    normalized = {str(k).lower().strip(): v for k, v in row.items()}
    return normalized.get(str(target_col).lower().strip())


def _scroll_to(driver: WebDriver, element) -> None:
    """Scroll element into center of view."""
    try:
        target = element if not isinstance(element, list) else element[0]
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", target
        )
        time.sleep(0.2)
    except Exception:
        pass

# def captcha_solve(driver:WebDriver,domain:str):
#     try:
#       if audio_btn := driver.find_element(By.XPATH,'//a[@class="BDC_SoundLink"]'):
#         audio_url = audio_btn.get_attribute("href")
#         driver.get(domain+audio_url)

#       time.sleep(1)
#       audio_element = driver.find_element(By.XPATH,"//audio")
#       audio_src = audio_element.get_attribute("src")
#       audio_content = requests.get(audio_src).content
#       with open("captcha.mp3", "wb") as f:
#         f.write(audio_content)
#       audio_text = pytesseract.image_to_string(Image.open("captcha.mp3"))
#       captcha_input = driver.find_element(By.XPATH,"//input[@id='captchaFormLayout_reqstOpenCaptchaTextBox_CD']")
#       captcha_input.send_keys(audio_text)
#       time.sleep(1)
#     except Exception as e:
#       log.error(f"Failed to solve captcha: {e}")