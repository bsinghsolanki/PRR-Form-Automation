"""
utils/captcha_image_solver.py
==============================
Solves BDC image captcha using:
  1. Screenshot of captcha element only
  2. OpenCV image preprocessing
  3. Tesseract OCR to read text
  4. Type solution into input box
"""

import os
import time
import cv2
import numpy as np
import pytesseract
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from utils.logger import get_logger

log = get_logger(__name__)

# ── Temp folder for captcha images ────────────────────
IMG_DIR = "temp_captcha"
os.makedirs(IMG_DIR, exist_ok=True)


class CaptchaImageSolver:
    """
    Solves BDC image captcha using OpenCV + Tesseract.

    Usage:
        solver  = CaptchaImageSolver(driver)
        success = solver.solve()
    """

    # ── Captcha IMAGE element XPaths ──────────────────
    CAPTCHA_IMG_XPATHS = [
        # '//div[@class="BDC_CaptchaImageDiv"]',
        '//td[@id="captchaFormLayout_0"]//img[@class="BDC_CaptchaImage"]',
        '//td[@id="captchaFormLayout_0"]//img[@alt="Retype the CAPTCHA code from the image"]',
        '//img[contains(@src,"BDC_captcha")]',
        '//img[contains(@id,"c_default_ctl")]',
        '//img[contains(@class,"BDC")]',
        '//img[contains(@id,"captcha")]',
        '//img[contains(@src,"captcha")]',
        '//*[contains(@class,"BDC_captchaCell")]//img',
    ]

    # ── Captcha INPUT element XPaths ──────────────────
    CAPTCHA_INPUT_XPATHS = [
        '//input[@name="captchaFormLayout$reqstOpenCaptchaTextBox"]',
        '//input[contains(@id,"BDC_VCID")]',
        '//input[contains(@name,"captcha")]',
        '//input[contains(@id,"captcha")]',
        '//img[contains(@id,"BDC")]'
        '/following::input[@type="text"][1]',
        '//img[contains(@src,"captcha")]'
        '/following::input[@type="text"][1]',
    ]
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait   = WebDriverWait(driver, 10)

    # ─────────────────────────────────────────────────
    # MAIN SOLVE
    # ─────────────────────────────────────────────────

    def solve(self, record=None) -> bool:
        """
        Full image captcha solve flow.
        
        Args:
            record : Record object (used for naming screenshots)
        """
        log.info("🔍 Looking for image captcha …")

        captcha_el = self._find_captcha_element()
        if not captcha_el:
            log.info("✅ No captcha found — skipping")
            return True

        log.info("🎯 Captcha image found — solving with OpenCV …")

        try:
            # ── Scroll to captcha ──────────────────────────
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                captcha_el
            )
            time.sleep(0.8)

            # ── Build meaningful filename from URL ─────────
            img_name = self._build_image_name(record)

            # ── Screenshot captcha element ─────────────────
            img_path = self._screenshot_element(captcha_el, img_name)

            # ── Verify file actually exists ────────────────
            if not img_path or not os.path.exists(img_path):
                log.error("❌ Screenshot file not found on disk")
                # ── Try finding it in temp folder ──────────
                img_path = self._find_latest_screenshot()
                if not img_path:
                    log.error("❌ No screenshot found in temp folder")
                    return False
                log.info(f"✅ Using existing screenshot: {img_path}")

            # Verify file has content
            file_size = os.path.getsize(img_path)
            log.info(f"📁 Screenshot file: {img_path} ({file_size} bytes)")

            if file_size < 100:
                log.error(f"❌ Screenshot file too small: {file_size} bytes")
                return False

            # ── Try all preprocessing methods ─────────────
            text = self._try_all_preprocessing(img_path)

            if not text or len(text) < 3:
                log.error(f"❌ OCR result too short: '{text}'")
                # Save failed attempt for debugging
                self._save_debug(img_path, f"FAILED_{img_name}")
                return False

            log.info(f"✅ Captcha solved: '{text}'")

            # ── Enter solution ─────────────────────────────
            success = self._enter_solution(text)
            return success

        except Exception as e:
            log.error(f"❌ Image captcha solve failed → {e}")
            return False


    def _build_image_name(self, record=None) -> str:
        """
        Build a meaningful image filename from the record URL.

        Examples:
            https://boca-raton.gov/portal  → bocaRaton_row2
            https://miami.fl.gov/request   → miami_row3
            None                           → captcha_timestamp
        """
        try:
            from urllib.parse import urlparse
            import re

            if record and record.url:
                parsed   = urlparse(record.url)
                # Get domain without www. and .gov/.com etc
                domain   = parsed.netloc.replace("www.", "")
                # Take first part of domain e.g. "boca-raton" from "boca-raton.gov"
                domain   = domain.split(".")[0]
                # Clean special chars
                domain   = re.sub(r'[^a-zA-Z0-9]', '_', domain)
                row      = f"row{record.row_number}" if record.row_number else ""
                name     = f"{domain}_{row}"

            else:
                # Fallback to current page URL
                current  = self.driver.current_url
                parsed   = urlparse(current)
                domain   = parsed.netloc.replace("www.", "").split(".")[0]
                domain   = re.sub(r'[^a-zA-Z0-9]', '_', domain)
                timestamp = int(time.time())
                name     = f"{domain}_{timestamp}"

            log.info(f"📛 Image name: '{name}'")
            return name

        except Exception:
            import time as t
            return f"captcha_{int(t.time())}"


    def _screenshot_element(self, element, img_name: str = "captcha") -> str | None:
        """
        Take screenshot of ONLY the captcha element.
        Uses meaningful filename based on URL/record.

        Returns:
            Path to saved captcha image or None
        """
        try:
            crop_path = os.path.join(IMG_DIR, f"{img_name}_captcha.png")

            # ── Method 1: Selenium direct element screenshot
            try:
                element.screenshot(crop_path)

                if os.path.exists(crop_path):
                    img      = Image.open(crop_path)
                    w, h     = img.size
                    log.info(f"✅ Direct screenshot: {crop_path} ({w}x{h})")

                    if w > 30 and h > 20:
                        self._save_debug(crop_path, f"{img_name}_method1")
                        return crop_path

                    log.warning(f"⚠️  Too small {w}x{h} — trying method 2")

            except Exception as e:
                log.warning(f"⚠️  Direct screenshot failed → {e}")

            # ── Method 2: Viewport-based crop ──────────────
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    element
                )
                time.sleep(0.8)

                loc  = element.location_once_scrolled_into_view
                size = element.size
                x, y = int(loc["x"]),   int(loc["y"])
                w, h = int(size["width"]), int(size["height"])

                full_path = os.path.join(IMG_DIR, f"{img_name}_fullpage.png")
                self.driver.save_screenshot(full_path)

                full_img       = Image.open(full_path)
                img_w, img_h   = full_img.size
                viewport_w     = self.driver.execute_script("return window.innerWidth")
                viewport_h     = self.driver.execute_script("return window.innerHeight")
                scale_x        = img_w / viewport_w
                scale_y        = img_h / viewport_h

                padding = 8
                x1 = max(0,     int(x * scale_x) - padding)
                y1 = max(0,     int(y * scale_y) - padding)
                x2 = min(img_w, int((x + w) * scale_x) + padding)
                y2 = min(img_h, int((y + h) * scale_y) + padding)

                log.info(f"✂️  Crop: ({x1},{y1})→({x2},{y2}) scale=({scale_x:.2f},{scale_y:.2f})")

                cropped = full_img.crop((x1, y1, x2, y2))
                cropped.save(crop_path)
                self._save_debug(crop_path, f"{img_name}_method2")
                log.info(f"✅ Method 2 screenshot: {crop_path}")
                return crop_path

            except Exception as e:
                log.warning(f"⚠️  Method 2 failed → {e}")

            # ── Method 3: JS getBoundingClientRect ──────────
            try:
                rect = self.driver.execute_script("""
                    var r = arguments[0].getBoundingClientRect();
                    return {x:r.left, y:r.top, right:r.right, bottom:r.bottom,
                            width:r.width, height:r.height};
                """, element)

                full_path = os.path.join(IMG_DIR, f"{img_name}_fullpage.png")
                self.driver.save_screenshot(full_path)
                full_img      = Image.open(full_path)
                img_w, img_h  = full_img.size
                viewport_w    = self.driver.execute_script("return window.innerWidth")
                scale         = img_w / viewport_w

                x1 = max(0,     int(rect["x"]      * scale) - 5)
                y1 = max(0,     int(rect["y"]      * scale) - 5)
                x2 = min(img_w, int(rect["right"]  * scale) + 5)
                y2 = min(img_h, int(rect["bottom"] * scale) + 5)

                cropped = full_img.crop((x1, y1, x2, y2))
                cropped.save(crop_path)
                self._save_debug(crop_path, f"{img_name}_method3")
                log.info(f"✅ Method 3 screenshot: {crop_path}")
                return crop_path

            except Exception as e:
                log.warning(f"⚠️  Method 3 failed → {e}")

            return None

        except Exception as e:
            log.error(f"❌ Screenshot error → {e}")
            return None


    def _find_latest_screenshot(self) -> str | None:
        """
        Find the most recently created image in temp folder.
        Fallback when screenshot path is lost.
        """
        try:
            files = [
                os.path.join(IMG_DIR, f)
                for f in os.listdir(IMG_DIR)
                if f.endswith(".png") and "captcha" in f
                and "fullpage" not in f
                and "debug" not in f
            ]

            if not files:
                return None

            # Return most recently modified
            latest = max(files, key=os.path.getmtime)
            log.info(f"📁 Found latest screenshot: {latest}")
            return latest

        except Exception as e:
            log.debug(f"Find latest error → {e}")
            return None


    def cleanup_temp(self, record=None) -> None:
        """
        Clean temp captcha folder after form submission.
        Keeps debug images, deletes processing intermediates.

        Args:
            record : If provided, only deletes files for this record
        """
        try:
            if not os.path.exists(IMG_DIR):
                return

            deleted = 0
            kept    = 0

            for filename in os.listdir(IMG_DIR):
                filepath = os.path.join(IMG_DIR, filename)

                # ── Keep debug files for review ────────────
                if "FAILED" in filename:
                    kept += 1
                    continue

                # ── Delete only this record's files ────────
                if record:
                    img_name = self._build_image_name(record)
                    if img_name not in filename:
                        kept += 1
                        continue

                os.remove(filepath)
                deleted += 1

            log.info(
                f"🗑️  Cleanup: deleted={deleted} kept={kept} "
                f"in {IMG_DIR}/"
            )

        except Exception as e:
            log.warning(f"⚠️  Cleanup error → {e}")

    # ─────────────────────────────────────────────────
    # FIND CAPTCHA ELEMENT
    # ─────────────────────────────────────────────────

    def _find_captcha_element(self):
        """Find and return the captcha image WebElement."""
        for xpath in self.CAPTCHA_IMG_XPATHS:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements:
                    log.info(f"🎯 Captcha img found: {xpath[:60]}")
                    return elements[0]
            except Exception:
                continue
        return None

    # ─────────────────────────────────────────────────
    # SCREENSHOT ELEMENT ONLY
    # ─────────────────────────────────────────────────

    # def _screenshot_element(self, element) -> str | None:
    #   """
    #   Take a screenshot of ONLY the captcha element.
    #   Uses Selenium's built-in element screenshot first,
    #   falls back to manual crop if that fails.

    #   Returns:
    #       Path to saved captcha image or None
    #   """
    #   try:
    #       crop_path = os.path.join(IMG_DIR, "captcha_crop.png")

    #       # ── Method 1: Selenium direct element screenshot
    #       # Most accurate — no coordinate math needed
    #       try:
    #           element.screenshot(crop_path)
    #           img = Image.open(crop_path)
    #           w, h = img.size
    #           log.info(f"✅ Direct element screenshot: {w}x{h}px")

    #           # Verify it's not empty or wrong element
    #           if w > 30 and h > 20:
    #               self._save_debug(crop_path, "method1_direct")
    #               return crop_path
    #           else:
    #               log.warning(f"⚠️  Element screenshot too small: {w}x{h}")

    #       except Exception as e:
    #           log.warning(f"⚠️  Direct screenshot failed → {e}")

    #       # ── Method 2: Scroll + location_once_scrolled_into_view
    #       try:
    #           # Scroll element into view first
    #           self.driver.execute_script(
    #               "arguments[0].scrollIntoView({block:'center'});",
    #               element
    #           )
    #           time.sleep(0.8)

    #           # Use scrolled location (more accurate than .location)
    #           loc  = element.location_once_scrolled_into_view
    #           size = element.size

    #           x = int(loc["x"])
    #           y = int(loc["y"])
    #           w = int(size["width"])
    #           h = int(size["height"])

    #           log.info(f"📐 Scrolled location: x={x} y={y} w={w} h={h}")

    #           # ── Screenshot visible viewport only ──────
    #           full_path = os.path.join(IMG_DIR, "full_page.png")
    #           self.driver.save_screenshot(full_path)

    #           full_img      = Image.open(full_path)
    #           img_w, img_h  = full_img.size

    #           # ── Get viewport dimensions (not full page) 
    #           viewport_w = self.driver.execute_script(
    #               "return window.innerWidth"
    #           )
    #           viewport_h = self.driver.execute_script(
    #               "return window.innerHeight"
    #           )

    #           log.info(f"🖥️  Viewport: {viewport_w}x{viewport_h}")
    #           log.info(f"📸 Screenshot: {img_w}x{img_h}")

    #           # ── Scale based on viewport not full page ──
    #           scale_x = img_w / viewport_w
    #           scale_y = img_h / viewport_h

    #           # ── Scale coordinates ──────────────────────
    #           x1 = int(x * scale_x)
    #           y1 = int(y * scale_y)
    #           x2 = int((x + w) * scale_x)
    #           y2 = int((y + h) * scale_y)

    #           # ── Add padding ────────────────────────────
    #           padding = 8
    #           x1 = max(0, x1 - padding)
    #           y1 = max(0, y1 - padding)
    #           x2 = min(img_w, x2 + padding)
    #           y2 = min(img_h, y2 + padding)

    #           log.info(f"✂️  Crop coords: ({x1},{y1}) → ({x2},{y2})")

    #           cropped = full_img.crop((x1, y1, x2, y2))
    #           cw, ch  = cropped.size
    #           log.info(f"✅ Cropped size: {cw}x{ch}px")

    #           cropped.save(crop_path)
    #           self._save_debug(crop_path, "method2_scrolled")
    #           return crop_path

    #       except Exception as e:
    #           log.warning(f"⚠️  Method 2 failed → {e}")

    #       # ── Method 3: JavaScript getBoundingClientRect ──
    #       try:
    #           log.info("🔄 Trying JS getBoundingClientRect …")

    #           rect = self.driver.execute_script("""
    #               var rect = arguments[0].getBoundingClientRect();
    #               return {
    #                   x      : rect.left,
    #                   y      : rect.top,
    #                   width  : rect.width,
    #                   height : rect.height,
    #                   right  : rect.right,
    #                   bottom : rect.bottom
    #               };
    #           """, element)

    #           log.info(f"📐 JS rect: {rect}")

    #           # Screenshot current viewport
    #           full_path = os.path.join(IMG_DIR, "full_page.png")
    #           self.driver.save_screenshot(full_path)
    #           full_img     = Image.open(full_path)
    #           img_w, img_h = full_img.size

    #           viewport_w = self.driver.execute_script("return window.innerWidth")
    #           scale      = img_w / viewport_w

    #           x1 = max(0,     int(rect["x"]      * scale) - 5)
    #           y1 = max(0,     int(rect["y"]      * scale) - 5)
    #           x2 = min(img_w, int(rect["right"]  * scale) + 5)
    #           y2 = min(img_h, int(rect["bottom"] * scale) + 5)

    #           log.info(f"✂️  JS crop: ({x1},{y1}) → ({x2},{y2})")

    #           cropped = full_img.crop((x1, y1, x2, y2))
    #           cropped.save(crop_path)
    #           self._save_debug(crop_path, "method3_js_rect")
    #           return crop_path

    #       except Exception as e:
    #           log.warning(f"⚠️  Method 3 failed → {e}")

    #       log.error("❌ All screenshot methods failed")
    #       return None

    #   except Exception as e:
    #       log.error(f"❌ Screenshot error → {e}")
    #       return None
    
    # ─────────────────────────────────────────────────
    # TRY ALL PREPROCESSING METHODS
    # ─────────────────────────────────────────────────

    def _try_all_preprocessing(self, img_path: str) -> str | None:
        """
        Try multiple OpenCV preprocessing pipelines.
        Log every result so we can see what is happening.
        """
        # ── First verify image loads correctly ────────────
        try:
            test_img = cv2.imread(img_path)
            if test_img is None:
                log.error(f"❌ cv2.imread returned None for: {img_path}")
                # Try loading with PIL instead
                pil_img  = Image.open(img_path)
                pil_img  = pil_img.convert("RGB")
                test_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                # Save as clean png for cv2
                fixed_path = os.path.join(IMG_DIR, "fixed_input.png")
                cv2.imwrite(fixed_path, test_img)
                img_path = fixed_path
                log.info(f"✅ Image fixed via PIL: {img_path}")

            h, w = test_img.shape[:2]
            log.info(f"📐 Input image size: {w}x{h}px")

        except Exception as e:
            log.error(f"❌ Image load error → {e}")
            return None

        # ── Run all pipelines ──────────────────────────────
        results  = []
        pipelines = [
              ("outline_font",            self._preprocess_outline_font),    # ← ADD FIRST
              ("grayscale_threshold",     self._preprocess_grayscale_threshold),
              ("invert_threshold",        self._preprocess_invert),
              ("upscale_threshold",       self._preprocess_upscale),
              ("adaptive_threshold",      self._preprocess_adaptive),
              ("raw_grayscale",           self._preprocess_raw),
          ]

        for name, pipeline in pipelines:
            try:
                processed_path = pipeline(img_path)
                if not processed_path or not os.path.exists(processed_path):
                    log.warning(f"⚠️  Pipeline '{name}' produced no output")
                    continue

                # ── Run OCR on processed image ─────────────
                raw_text = self._ocr(processed_path)
                clean    = self._clean_text(raw_text)

                log.info(
                    f"  🔬 [{name}]"
                    f" raw='{raw_text}'"
                    f" clean='{clean}'"
                    f" len={len(clean)}"
                )

                if clean and len(clean) >= 3:
                    results.append((len(clean), clean, name))

            except Exception as e:
                log.warning(f"⚠️  Pipeline '{name}' error → {e}")
                continue

        if not results:
            # ── Last resort: raw OCR on original image ─────
            log.warning("⚠️  All pipelines failed — trying raw OCR on original")
            try:
                raw_text = self._ocr(img_path)
                clean    = self._clean_text(raw_text)
                log.info(f"  🔬 [raw_original] raw='{raw_text}' clean='{clean}'")
                if clean:
                    return clean
            except Exception as e:
                log.error(f"❌ Raw OCR also failed → {e}")
            return None

        # ── Pick result closest to 6 chars ────────────────
        results.sort(key=lambda x: abs(x[0] - 6))
        best_len, best_text, best_name = results[0]
        log.info(f"✅ Best result [{best_name}]: '{best_text}' ({best_len} chars)")
        return best_text


    def _ocr(self, img_path: str) -> str:
      try:
          try:
              version = pytesseract.get_tesseract_version()
              log.debug(f"Tesseract version: {version}")
          except Exception:
              log.error("❌ Tesseract not found! sudo apt install tesseract-ocr -y")
              return ""

          img = Image.open(img_path)
          log.debug(f"🔍 OCR on: {img_path} size={img.size}")

          configs = [
              # Best for captcha — uppercase + digits, single word
              r"--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
              # Single line
              r"--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
              # Uniform block
              r"--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
              # Both cases — uppercase after
              r"--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
              r"--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
              # No whitelist fallback
              r"--psm 8 --oem 3",
              r"--psm 7 --oem 3",
              r"--psm 8 --oem 0",
          ]

          for config in configs:
              try:
                  text = pytesseract.image_to_string(
                      img,
                      config=config
                  ).strip()

                  if text:
                      text = text.upper()
                      log.debug(f"  OCR → '{text}'")
                      return text

              except Exception as e:
                  log.debug(f"  OCR config failed → {e}")
                  continue

          log.warning("⚠️  All OCR configs returned empty")
          return ""

      except Exception as e:
          log.error(f"❌ OCR error → {e}")
          return ""

    # ─────────────────────────────────────────────────
    # PREPROCESSING PIPELINES
    # ─────────────────────────────────────────────────

    def _preprocess_grayscale_threshold(self, img_path: str) -> str | None:
        """
        Pipeline 1: Standard grayscale + binary threshold + denoise.
        Best for: dark text on light background.
        """
        try:
            img  = cv2.imread(img_path)

            # ── Upscale 3x for better OCR ──────────────
            img  = cv2.resize(
                img, None, fx=3, fy=3,
                interpolation=cv2.INTER_CUBIC
            )

            # ── Convert to grayscale ───────────────────
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # ── Remove noise ──────────────────────────
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            gray = cv2.medianBlur(gray, 3)

            # ── Binary threshold ───────────────────────
            _, thresh = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            # ── Dilate to connect broken characters ───
            kernel = np.ones((2, 2), np.uint8)
            thresh = cv2.dilate(thresh, kernel, iterations=1)

            out_path = os.path.join(IMG_DIR, "p1_gray_thresh.png")
            cv2.imwrite(out_path, thresh)
            return out_path

        except Exception as e:
            log.debug(f"Pipeline 1 error → {e}")
            return None

    def _preprocess_invert(self, img_path: str) -> str | None:
        """
        Pipeline 2: Invert colors + threshold.
        Best for: light text on dark background.
        """
        try:
            img  = cv2.imread(img_path)
            img  = cv2.resize(
                img, None, fx=3, fy=3,
                interpolation=cv2.INTER_CUBIC
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # ── Invert ────────────────────────────────
            gray = cv2.bitwise_not(gray)

            _, thresh = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            out_path = os.path.join(IMG_DIR, "p2_invert.png")
            cv2.imwrite(out_path, thresh)
            return out_path

        except Exception as e:
            log.debug(f"Pipeline 2 error → {e}")
            return None

    def _preprocess_upscale(self, img_path: str) -> str | None:
        """
        Pipeline 3: Aggressive upscale + sharpen.
        Best for: small or blurry captchas.
        """
        try:
            img  = cv2.imread(img_path)

            # ── Upscale 5x ─────────────────────────────
            img  = cv2.resize(
                img, None, fx=5, fy=5,
                interpolation=cv2.INTER_LANCZOS4
            )

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # ── Sharpen ───────────────────────────────
            kernel = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            gray = cv2.filter2D(gray, -1, kernel)

            _, thresh = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            out_path = os.path.join(IMG_DIR, "p3_upscale.png")
            cv2.imwrite(out_path, thresh)
            return out_path

        except Exception as e:
            log.debug(f"Pipeline 3 error → {e}")
            return None

    def _preprocess_adaptive(self, img_path: str) -> str | None:
        """
        Pipeline 4: Adaptive threshold.
        Best for: uneven lighting or gradient backgrounds.
        """
        try:
            img  = cv2.imread(img_path)
            img  = cv2.resize(
                img, None, fx=3, fy=3,
                interpolation=cv2.INTER_CUBIC
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5, 5), 0)

            # ── Adaptive threshold ─────────────────────
            thresh = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize = 11,
                C         = 2
            )

            out_path = os.path.join(IMG_DIR, "p4_adaptive.png")
            cv2.imwrite(out_path, thresh)
            return out_path

        except Exception as e:
            log.debug(f"Pipeline 4 error → {e}")
            return None

    def _preprocess_raw(self, img_path: str) -> str | None:
        """
        Pipeline 5: Just upscale and grayscale, no threshold.
        Fallback for when thresholding hurts more than helps.
        """
        try:
            img  = cv2.imread(img_path)
            img  = cv2.resize(
                img, None, fx=3, fy=3,
                interpolation=cv2.INTER_CUBIC
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            out_path = os.path.join(IMG_DIR, "p5_raw.png")
            cv2.imwrite(out_path, gray)
            return out_path

        except Exception as e:
            log.debug(f"Pipeline 5 error → {e}")
            return None

    # ─────────────────────────────────────────────────
    # OCR
    # ─────────────────────────────────────────────────

    # def _ocr(self, img_path: str) -> str:
    #     """
    #     Run Tesseract OCR on processed image.
    #     Uses config optimized for captcha text.
    #     """
    #     try:
    #         img = Image.open(img_path)

    #         # ── Tesseract config ───────────────────────
    #         # psm 8 = single word
    #         # psm 7 = single line
    #         # oem 3 = best LSTM engine
    #         configs = [
    #             "--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    #             "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    #             "--psm 6 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    #         ]

    #         for config in configs:
    #             text = pytesseract.image_to_string(
    #                 img,
    #                 config=config
    #             ).strip()
    #             if text:
    #                 return text

    #         return ""

    #     except Exception as e:
    #         log.debug(f"OCR error → {e}")
    #         return ""

    # ─────────────────────────────────────────────────
    # CLEAN TEXT
    # ─────────────────────────────────────────────────

    def _clean_text(self, text: str) -> str:
      """Remove non-alphanumeric characters and uppercase."""
      import re
      if not text:
          return ""
      # Keep only letters and numbers
      clean = re.sub(r'[^A-Z0-9]', '', text.upper())
      log.debug(f"🧹 Cleaned: '{text}' → '{clean}'")
      return clean

    # ─────────────────────────────────────────────────
    # ENTER SOLUTION
    # ─────────────────────────────────────────────────

    def _enter_solution(self, text: str) -> bool:
        """Type the captcha solution into the input box."""
        for xpath in self.CAPTCHA_INPUT_XPATHS:
            try:
                input_el = self.driver.find_element(By.XPATH, xpath)
                input_el.clear()
                input_el.send_keys(text)
                log.info(f"✅ Captcha entered: '{text}'")
                time.sleep(0.3)
                return True
            except NoSuchElementException:
                continue
            except Exception as e:
                log.debug(f"Input error → {e}")
                continue

        log.error("❌ Captcha input field not found")
        return False

    # ─────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────

    def cleanup(self) -> None:
        """Delete all temp captcha images."""
        try:
            import shutil
            if os.path.exists(IMG_DIR):
                shutil.rmtree(IMG_DIR)
                os.makedirs(IMG_DIR, exist_ok=True)
                log.debug("🗑️  Captcha temp images cleaned")
        except Exception as e:
            log.debug(f"Cleanup error → {e}")
    
    def _save_debug(self, img_path: str, label: str) -> None:
      """Save a labeled debug copy of any image."""
      try:
          import shutil
          debug_path = os.path.join(IMG_DIR, f"debug_{label}.png")
          shutil.copy2(img_path, debug_path)
          log.info(f"🐛 Debug saved → {debug_path}")
      except Exception as e:
          log.debug(f"Debug save failed → {e}")
    
    def _preprocess_outline_font(self, img_path: str) -> str | None:
      """
      Pipeline specifically for outline/hollow white fonts
      on dark noisy backgrounds like this captcha.

      Steps:
        1. Upscale 4x
        2. Convert to grayscale
        3. Invert (white letters → black)
        4. Remove noise with morphological operations
        5. Fill hollow letters
        6. Binary threshold
      """
      try:
          img = cv2.imread(img_path)
          if img is None:
              pil_img = Image.open(img_path).convert("RGB")
              img     = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

          # ── Step 1: Upscale 4x ─────────────────────────
          img = cv2.resize(
              img, None, fx=4, fy=4,
              interpolation=cv2.INTER_LANCZOS4
          )

          # ── Step 2: Grayscale ──────────────────────────
          gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

          # ── Step 3: Remove background noise ───────────
          # Median blur removes speckle dots
          gray = cv2.medianBlur(gray, 5)
          gray = cv2.GaussianBlur(gray, (3, 3), 0)

          # ── Step 4: Invert ─────────────────────────────
          # White letters on dark → black letters on white
          gray = cv2.bitwise_not(gray)

          # ── Step 5: Threshold ──────────────────────────
          _, thresh = cv2.threshold(
              gray, 0, 255,
              cv2.THRESH_BINARY + cv2.THRESH_OTSU
          )

          # ── Step 6: Fill hollow letters ────────────────
          # Dilate fills the hollow outlines
          kernel = np.ones((3, 3), np.uint8)
          thresh = cv2.dilate(thresh, kernel, iterations=2)

          # ── Step 7: Erode to restore original size ─────
          thresh = cv2.erode(thresh, kernel, iterations=1)

          # ── Step 8: Remove small noise dots ───────────
          # Find contours and remove tiny ones
          contours, _ = cv2.findContours(
              thresh,
              cv2.RETR_EXTERNAL,
              cv2.CHAIN_APPROX_SIMPLE
          )

          # Create clean white image
          clean = np.ones_like(thresh) * 255

          for cnt in contours:
              area = cv2.contourArea(cnt)
              # Keep only contours big enough to be letters
              # Adjust min_area based on your captcha size
              if area > 100:
                  cv2.drawContours(clean, [cnt], -1, 0, -1)

          out_path = os.path.join(IMG_DIR, "p0_outline_font.png")
          cv2.imwrite(out_path, clean)
          log.info(f"✅ Outline font pipeline complete → {out_path}")
          return out_path

      except Exception as e:
          log.debug(f"Outline font pipeline error → {e}")
          return None