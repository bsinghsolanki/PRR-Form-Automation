"""
utils/captcha_manager.py
========================
Unified captcha manager.
Tries image solver first, audio solver as fallback.
"""

import time
from selenium.webdriver.remote.webdriver import WebDriver
from utils.logger import get_logger

log = get_logger(__name__)


class CaptchaManager:
    """
    Manages captcha solving with fallback strategy:
      1. Image solver (OpenCV + Tesseract) — fastest
      2. Audio solver (Whisper)            — fallback

    Usage:
        manager = CaptchaManager(driver)
        success = manager.solve(record)
    """

    def __init__(self, driver: WebDriver):
        self.driver = driver

    def solve(self, record=None) -> bool:
        """
        Try all captcha solving methods in order.

        Returns:
            True if solved or no captcha found
            False if all methods failed
        """
        log.info(f"🔐 [Row {getattr(record, 'row_number', '?')}] CaptchaManager starting …")

        # ── Method 1: Image solver ─────────────────────
        log.info("🖼️  Trying image captcha solver …")
        result = self._try_image_solver(record)

        if result is True:
            log.info("✅ Image solver succeeded")
            return True
        elif result == "no_captcha":
            log.info("✅ No captcha on page — skipping")
            return True

        log.warning("⚠️  Image solver failed — trying audio solver …")

        # ── Method 2: Audio solver ─────────────────────
        log.info("🎵 Trying audio captcha solver …")
        result = self._try_audio_solver(record)

        if result:
            log.info("✅ Audio solver succeeded")
            return True

        log.error("❌ All captcha solving methods failed")
        return False

    # ─────────────────────────────────────────────────
    # IMAGE SOLVER
    # ─────────────────────────────────────────────────

    def _try_image_solver(self, record=None):
        """
        Run image captcha solver.

        Returns:
            True        — solved successfully
            'no_captcha'— no captcha found on page
            False       — found but failed to solve
        """
        try:
            from utils.captcha_image_solver import CaptchaImageSolver

            solver     = CaptchaImageSolver(self.driver)
            captcha_el = solver._find_captcha_element()

            # ── No captcha found ───────────────────────
            if not captcha_el:
                return "no_captcha"

            log.info("🎯 Image captcha detected")

            # ── Scroll to it ───────────────────────────
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                captcha_el
            )
            time.sleep(0.8)

            # ── Screenshot ─────────────────────────────
            img_name = solver._build_image_name(record)
            img_path = solver._screenshot_element(captcha_el, img_name)

            if not img_path:
                import os
                img_path = solver._find_latest_screenshot()

            if not img_path:
                log.error("❌ No screenshot available")
                return False

            # ── OCR ────────────────────────────────────
            text = solver._try_all_preprocessing(img_path)

            if not text or len(text) < 3:
                log.error(f"❌ OCR result invalid: '{text}'")
                return False

            log.info(f"✅ Image OCR result: '{text}'")

            text = text.upper().strip()
            log.info(f"✅ Final captcha text (uppercase): '{text}'")

            # ── Enter solution ─────────────────────────
            return solver._enter_solution(text)

        except ImportError:
            log.warning("⚠️  CaptchaImageSolver not available")
            return False
        except Exception as e:
            log.error(f"❌ Image solver error → {e}")
            return False

    # ─────────────────────────────────────────────────
    # AUDIO SOLVER
    # ─────────────────────────────────────────────────

    def _try_audio_solver(self, record=None) -> bool:
        """
        Run audio captcha solver using Whisper.

        Returns:
            True  — solved successfully
            False — failed or no audio captcha found
        """
        try:
            from utils.captcha_solver import CaptchaSolver

            domain = ""
            if record:
                domain = getattr(record, "domain", "")

            solver = CaptchaSolver(self.driver, domain=domain)

            # ── Check if audio button exists ───────────
            from selenium.webdriver.common.by import By
            audio_found = False
            for xpath in solver.AUDIO_BTN_XPATHS:
                els = self.driver.find_elements(By.XPATH, xpath)
                if els:
                    audio_found = True
                    log.info(f"🔊 Audio button found: {xpath[:60]}")
                    break

            if not audio_found:
                log.info("ℹ️  No audio button found — skipping audio solver")
                return False

            return solver.solve()

        except ImportError:
            log.warning("⚠️  CaptchaSolver not available")
            return False
        except Exception as e:
            log.error(f"❌ Audio solver error → {e}")
            return False