import csv
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import Select

from field_detector import build_form_map

_CSV_HEADERS = ["URL", "Question_Label", "Field_Type", "Options_Found"]


def scrape_to_csv(driver: WebDriver, url: str, output_file: str = "form_requirements.csv") -> None:
    """
    Navigate to *url*, scrape all form fields, and append the results to *output_file*.

    Existing files are appended to (not overwritten); the header row is written
    only when the file does not yet exist or is empty.
    """
    driver.get(url)
    form_map = build_form_map(driver)

    output_path = Path(output_file)
    write_header = not output_path.exists() or output_path.stat().st_size == 0

    with output_path.open(mode="a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)

        if write_header:
            writer.writerow(_CSV_HEADERS)

        for label, meta in form_map.items():
            options = _extract_options(driver, meta)
            writer.writerow([
                url,
                label,
                meta["type"],
                " | ".join(options) if options else "N/A",
            ])

    print(f"✅ Scraped {len(form_map)} fields from {url}")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_options(driver: WebDriver, meta: dict) -> list[str]:
    """Return visible option texts for selection-type fields."""
    f_type = meta["type"]
    element = meta["element"]
    options: list[str] = []

    if f_type == "dropdown":
        options = [o.text.strip() for o in Select(element).options if o.text.strip()]

    elif f_type in ("radio", "checkbox"):
        for opt in element:
            try:
                opt_id = opt.get_attribute("id")
                lbl = driver.find_element(By.XPATH, f"//label[@for='{opt_id}']")
                text = lbl.text.strip()
                if text:
                    options.append(text)
            except Exception:
                # Fallback: try the parent element's text.
                try:
                    text = opt.find_element(By.XPATH, "..").text.strip()
                    if text:
                        options.append(text)
                except Exception:
                    continue

    return options
