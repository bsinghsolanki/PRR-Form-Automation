"""
form_filler.py
==============
Single entry point: ``fill_form(driver, row, form_map)``.

Resolution order for every field:
  1. DecisionEngine  — dates, signatures, legal questions, delivery, agreements
  2. FIELD_MAP       — static keyword → sheet-column mapping (constants.py)
  3. SemanticMatcher — fuzzy / synonym fallback against remaining sheet columns
"""

import time
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException

from engine.decision_engine import DecisionEngine
from engine.semantic_matcher import SemanticMatcher
from utils.constants import FIELD_MAP
from utils.normalizer import normalize


# ──────────────────────────────────────────────────────────────────────── #
# Public API
# ──────────────────────────────────────────────────────────────────────── #
def handle_department(driver, f_type, element, decision_engine):
    """
    Selects the best available department option using DEPARTMENT_PRIORITY.
    Returns True if a selection was made, False otherwise.
    """

    # ── DROPDOWN ─────────────────────────────────────────────────────────
    if f_type == "dropdown":
        sel = Select(element)
        available = [o.text.strip() for o in sel.options if o.text.strip()]
        best = decision_engine.pick_department(available)

        if best:
            sel.select_by_visible_text(best)
            print(f"🏢 Department dropdown → '{best}'")
        else:
            # Skip placeholder (index 0) and take first real option
            sel.select_by_index(1)
            print("🏢 Department dropdown → fallback index 1")
        return True

    # ── RADIO ─────────────────────────────────────────────────────────────
    if f_type == "radio":
        available_map = {}   # option_text → element
        for opt in element:
            try:
                opt_id  = opt.get_attribute("id")
                lbl_txt = driver.find_element(
                    By.XPATH, f"//label[@for='{opt_id}']"
                ).text.strip()
            except Exception:
                lbl_txt = (opt.get_attribute("value") or "").strip()
            if lbl_txt:
                available_map[lbl_txt] = opt

        best = decision_engine.pick_department(list(available_map.keys()))

        if best and best in available_map:
            opt_el = available_map[best]
            if not opt_el.is_selected():
                driver.execute_script("arguments[0].click();", opt_el)
            print(f"🏢 Department radio → '{best}'")
            return True

    # ── CHECKBOX (multi-select) ────────────────────────────────────────────
    if f_type == "checkbox":
        available_map = {}
        for opt in element:
            try:
                opt_id  = opt.get_attribute("id")
                lbl_txt = driver.find_element(
                    By.XPATH, f"//label[@for='{opt_id}']"
                ).text.strip()
            except Exception:
                lbl_txt = (opt.get_attribute("value") or "").strip()
            if lbl_txt:
                available_map[lbl_txt] = opt

        best = decision_engine.pick_department(list(available_map.keys()))

        if best and best in available_map:
            opt_el = available_map[best]
            if not opt_el.is_selected():
                driver.execute_script("arguments[0].click();", opt_el)
            print(f"🏢 Department checkbox → '{best}'")
            return True

    return False

def fill_form(driver: WebDriver, row: dict, form_map: dict) -> None:
    """
    Fill every field in *form_map* using data from *row* (a Google Sheet row dict).

    Args:
        driver:   Active Selenium WebDriver.
        row:      {column_name: value} dict from the spreadsheet.
        form_map: Output of ``field_detector.build_form_map()``.
    """
    today   = datetime.now().strftime("%m/%d/%Y")
    engine  = DecisionEngine()
    matcher = SemanticMatcher(list(row.keys()))

    print(f"🧠 Fields detected: {len(form_map)}")
    print("🔑 Sheet columns:", list(row.keys()))
    for label, meta in form_map.items():
        try:
            _fill_field(driver, row, label, meta, engine, matcher, today)
        except StaleElementReferenceException:
            print(f"⚠️  Stale element skipped: {label}")
        except Exception as exc:
            print(f"⚠️  Failed → '{label}': {exc}")


# ──────────────────────────────────────────────────────────────────────── #
# Per-field orchestration
# ──────────────────────────────────────────────────────────────────────── #

def _fill_field(
    driver:   WebDriver,
    row:      dict,
    label:    str,
    meta:     dict,
    engine:   DecisionEngine,
    matcher:  SemanticMatcher,
    today:    str,
) -> None:
    l        = normalize(label)
    f_type   = meta["type"]
    element  = meta["element"]
    required = meta["required"]

    _scroll_to(driver, element, f_type)

    # Gather visible options for selection fields
    options = _get_options(driver, f_type, element)

    # ── Step 1: Decision Engine ──────────────────────────────────────────
    decision = engine.decide(l, f_type, options)

    if decision == "__SKIP__":
        return

    if decision is not None:
        _apply_decision(driver, row, decision, f_type, element, options, today)
        return

    # ── Step 2: FIELD_MAP keyword lookup ────────────────────────────────
    sheet_col = _resolve_column(l, matcher)

    if not sheet_col:
        if required:
            print(f"🚨 REQUIRED field has no mapping: '{label}'")
        return
    if sheet_col == "Department" and f_type in ("dropdown", "radio", "checkbox"):
        if handle_department(driver, f_type, element, engine):
            return
    value = _get_row_value(row, sheet_col)
    if not value:
        if required:
            print(f"🚨 REQUIRED value missing for column: '{sheet_col}'")
        return
    if sheet_col.lower() == "email":
        email_textbox(driver,str(value))
        return
    # ── Step 3: Fill by type ─────────────────────────────────────────────
    _fill_by_type(driver, f_type, element, str(value))
    print(f"✅ Filled '{l}' ← '{sheet_col}' = {value!r}")


# ──────────────────────────────────────────────────────────────────────── #
# Decision application
# ──────────────────────────────────────────────────────────────────────── #

def _apply_decision(
    driver:   WebDriver,
    row:      dict,
    decision: str,
    f_type:   str,
    element,
    options:  list[str],
    today:    str,
) -> None:
    """Translate a DecisionEngine token into a Selenium action."""

    # ── Date ─────────────────────────────────────────────────────────────
    if decision == "__TODAY__":
        target = element if not isinstance(element, list) else element[0]
        driver.execute_script("arguments[0].value = arguments[1];", target, today)
        print(f"✅ Date set to {today}")
        return

    # ── Signature ────────────────────────────────────────────────────────
    if decision == "__SIGN__":
        name = _get_row_value(row, "Name")
        if name and f_type in ("text", "textarea"):
            element.clear()
            element.send_keys(name)
            print(f"✅ Signature filled: {name}")
        return

    if decision == "__REASON__":
        reason = "This request is submitted under applicable open records laws to access public purchasing records."
        if f_type in ("text", "textarea"):
            element.clear()
            element.send_keys(reason)
            print("✅ Reason filled")
        return
    # ── Description ──────────────────────────────────────────────────────
    if decision == "__DESCRIPTION__":
        desc = _get_row_value(row, "Description")
        if desc and f_type in ("text", "textarea"):
            element.clear()
            element.send_keys(desc)
            print("✅ Description filled")
        return

    # ── NJ OPRA — click every negative option ────────────────────────────
    if decision == "__NJ_OPRA_NEG__":
        _click_nj_opra_negatives(driver, element)
        return

    # ── "Receive email copy" single checkbox ─────────────────────────────
    if f_type == "checkbox" and isinstance(element, list) and len(element) == 1:
        if not element[0].is_selected():
            driver.execute_script("arguments[0].click();", element[0])
        print(f"✅ Checkbox clicked")
        return

    # ── Generic option string ─────────────────────────────────────────────
    if f_type in ("radio", "checkbox"):
        _click_matching_option(driver, element, decision)
    elif f_type == "dropdown":
        _select_dropdown(element, decision)
    elif f_type in ("text", "textarea"):
        element.clear()
        element.send_keys(decision)
        print(f"✅ Text set: {decision!r}")


# ──────────────────────────────────────────────────────────────────────── #
# NJ OPRA handler
# ──────────────────────────────────────────────────────────────────────── #

def _click_nj_opra_negatives(driver: WebDriver, elements) -> None:
    """
    For NJ OPRA triple-certification checkboxes, click every option that
    asserts the negative status (HAVE NOT / WILL NOT / AM NOT).
    """
    neg_targets = ["have not", "will not", "am not", "i am not"]
    clicked = 0

    for opt in (elements if isinstance(elements, list) else [elements]):
        lbl = _get_option_label(driver, opt)
        if any(t in lbl for t in neg_targets):
            if not opt.is_selected():
                driver.execute_script("arguments[0].click();", opt)
                time.sleep(0.3)
            clicked += 1

    print(f"✅ NJ OPRA: clicked {clicked} negative certification(s)")


# ──────────────────────────────────────────────────────────────────────── #
# Field-type fill helpers
# ──────────────────────────────────────────────────────────────────────── #

def _fill_by_type(driver: WebDriver, f_type: str, element, value: str) -> None:
    if f_type in ("text", "textarea", "date"):
        element.clear()
        element.send_keys(value)
    elif f_type == "dropdown":
        _select_dropdown(element, value)
    elif f_type in ("radio", "checkbox"):
        _click_matching_option(driver, element, value)


def _select_dropdown(element, target_text: str) -> None:
    sel = Select(element)
    target_lower = target_text.lower()

    for opt in sel.options:
        if target_lower in opt.text.lower():
            sel.select_by_visible_text(opt.text)
            print(f"✅ Dropdown → {opt.text!r}")
            return

    # Fallback: skip placeholder (index 0) and take first real option
    if len(sel.options) > 1:
        sel.select_by_index(1)
        print(f"⚠️  Dropdown fallback → index 1")
    elif sel.options:
        sel.select_by_index(0)


def _click_matching_option(driver: WebDriver, elements, target_text: str) -> None:
    target_lower = target_text.lower()

    for opt in (elements if isinstance(elements, list) else [elements]):
        lbl = _get_option_label(driver, opt)
        if target_lower in lbl:
            if not opt.is_selected():
                driver.execute_script("arguments[0].click();", opt)
                print(f"✅ Selected: {lbl!r}")
            return


# ──────────────────────────────────────────────────────────────────────── #
# Option / column helpers
# ──────────────────────────────────────────────────────────────────────── #

def _get_options(driver: WebDriver, f_type: str, element) -> list[str]:
    if f_type == "dropdown":
        return [o.text.strip() for o in Select(element).options if o.text.strip()]

    if f_type in ("radio", "checkbox"):
        labels = []
        for opt in (element if isinstance(element, list) else [element]):
            text = _get_option_label(driver, opt)
            if text:
                labels.append(text)
        return labels

    return []


def _get_option_label(driver: WebDriver, opt_element) -> str:
    """Return the visible label text for a radio/checkbox input (lowercased)."""
    try:
        opt_id = opt_element.get_attribute("id")
        if opt_id:
            lbl = driver.find_element(By.XPATH, f"//label[@for='{opt_id}']")
            return lbl.text.lower().strip()
    except Exception:
        pass

    for attr in ("aria-label", "value"):
        val = opt_element.get_attribute(attr)
        if val:
            return val.lower().strip()

    try:
        return opt_element.find_element(By.XPATH, "..").text.lower().strip()
    except Exception:
        return ""


def _resolve_column(label: str, matcher: SemanticMatcher) -> str | None:
    for keyword, column in FIELD_MAP.items():
        if keyword in label:
            return column
    return matcher.match(label)


def _get_row_value(row: dict, target_col: str) -> str | None:
    """Case/whitespace-insensitive row accessor."""
    normalised = {str(k).lower().strip(): v for k, v in row.items()}
    return normalised.get(str(target_col).lower().strip())


def _scroll_to(driver: WebDriver, element, f_type: str) -> None:
    try:
        target = element if not isinstance(element, list) else element[0]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
    except Exception:
        pass

def select_email_delivery(driver: WebDriver, email_value: str = "") -> None:
    """
    After fill_form(), call this to:
    1. Click any radio/checkbox with value='email' that was missed
    2. Fill any email textboxes that field_detector may have missed
    """
    # Click radio/checkbox with value="email"
    try:
        email_option = driver.find_element(
            By.XPATH,
            "//input[(@type='radio' or @type='checkbox') "
            "and translate(@value,'EMAIL','email')='email']"
        )
        if not email_option.is_selected():
            driver.execute_script("arguments[0].click();", email_option)
        print("✅ Email delivery radio/checkbox selected")
    except Exception:
        print("⚠️ No email delivery radio/checkbox found")
 
    # Fill any email textboxes
    if email_value:
        email_textbox(driver, email_value)


def email_textbox(driver,value):
    try:
        if email_textbox := driver.find_element(
            By.XPATH,
            "//li//label[contains(text(),'Email')]/following-sibling::div//input[@type='text']"):
            email_textbox.send_keys(value)

            print("✅ Email delivery selected")

    except Exception:
        print("⚠️ No email delivery option found")

def email_textbox(driver: WebDriver, value: str) -> None:
    """
    Fill every visible, empty text/email input whose associated label
    contains the word 'email' (case-insensitive).
 
    Tries five XPath patterns covering all known CivicPlus DOM layouts.
    Uses find_elements (plural) so multiple email fields on one page
    (e.g. "Email" + "Reply Email" + "Email address") are all filled.
    Skips inputs that are already filled to avoid overwriting.
    """
    PATTERNS = [
        # 1. Standard CivicPlus — label sibling, input directly after
        "//label[contains(translate(normalize-space(.),'EMAIL','email'),'email')]"
        "/following-sibling::input[@type='text' or @type='email']",
 
        # 2. Standard CivicPlus — label → sibling div → input (most common)
        "//label[contains(translate(normalize-space(.),'EMAIL','email'),'email')]"
        "/following-sibling::div//input[@type='text' or @type='email']",
 
        # 3. li-based layout (e.g. "Reply Email" in Barrington RI)
        "//li//label[contains(translate(normalize-space(.),'EMAIL','email'),'email')]"
        "/following-sibling::div//input[@type='text' or @type='email']",
 
        # 4. Label wraps/ancestors the input
        "//label[contains(translate(normalize-space(.),'EMAIL','email'),'email')]"
        "//input[@type='text' or @type='email']",
 
        # 5. Input whose own placeholder or aria-label mentions email
        "//input[(@type='text' or @type='email') and ("
        "contains(translate(@placeholder,'EMAIL','email'),'email') or "
        "contains(translate(@aria-label,'EMAIL','email'),'email'))]",
    ]
 
    filled = 0
    seen   = set()   # avoid filling same element twice via different patterns
 
    for xpath in PATTERNS:
        try:
            inputs = driver.find_elements(By.XPATH, xpath)
            for el in inputs:
                el_id = el.id   # Selenium internal element ID — unique per element
                if el_id in seen:
                    continue
                if not el.is_displayed() or not el.is_enabled():
                    continue
                current = (el.get_attribute("value") or "").strip()
                if current:
                    seen.add(el_id)
                    continue    # already filled — skip
                el.clear()
                el.send_keys(value)
                seen.add(el_id)
                filled += 1
                print(f"✅ Email textbox filled (pattern {PATTERNS.index(xpath)+1})")
        except Exception:
            continue
 
    if filled == 0:
        print("⚠️ email_textbox: no empty email input found on page")

