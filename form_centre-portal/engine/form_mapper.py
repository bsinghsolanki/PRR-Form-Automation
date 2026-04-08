"""
form_mapper.py
==============
Higher-level orchestrator: detects fields then delegates to ``fill_form``.
Use this when you want a single call to handle navigation + filling.
"""

import logging

from selenium.webdriver.remote.webdriver import WebDriver

from engine.field_detector import build_form_map
from form_filler import fill_form

logger = logging.getLogger(__name__)


class FormMapper:
    """
    Orchestrates field detection and form filling for a single page.

    Usage::

        mapper = FormMapper()
        mapper.fill(driver, row)
    """

    def fill(self, driver: WebDriver, row: dict) -> None:
        """
        Detect all form fields on the current page and fill them from *row*.

        Args:
            driver: Active Selenium WebDriver positioned on the target page.
            row:    Dict of {sheet_column: value} for the current request.
        """
        logger.info("Detecting form fields…")
        form_map = build_form_map(driver)
        logger.info("Found %d fields.", len(form_map))

        fill_form(driver, row, form_map)
