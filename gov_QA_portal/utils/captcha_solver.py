"""
utils/captcha_solver.py
=======================
Solves audio captcha by:
  1. Detecting captcha on page
  2. Clicking audio button
  3. Downloading audio file
  4. Converting audio to text using SpeechRecognition
  5. Typing solution into captcha input
"""

import os
import time
import requests
import speech_recognition as sr
from pydub import AudioSegment
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from utils.logger import get_logger

log = get_logger(__name__)

# ── Temp folder for audio files ────────────────────────
AUDIO_DIR = "temp_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


class CaptchaSolver:
    """
    Solves audio captcha on portal pages.

    Usage:
        solver  = CaptchaSolver(driver)
        success = solver.solve()
    """

    # ── Captcha frame XPaths ───────────────────────────
    CAPTCHA_PRESENT_XPATHS = [
        '//div[@id="captchaFormLayout"]',
        # '//iframe[contains(@title,"recaptcha")]',
        # '//iframe[contains(@src,"captcha")]',
        # '//div[@class="g-recaptcha"]//iframe',
    ]

    # ── Audio button XPaths ────────────────────────────
    AUDIO_BTN_XPATHS = [
        '//a[@class="BDC_SoundLink"]',              # BetterDeadCenter captcha
        '//button[@id="recaptcha-audio-button"]',    # Google reCAPTCHA
        '//*[@id="recaptcha-audio-button"]',
        '//button[contains(@class,"audio")]',
        '//*[@title="Get an audio challenge"]',
    ]

    # ── Audio download link XPaths ─────────────────────
    AUDIO_SRC_XPATHS = [
        '//a[@class="BDC_SoundLink"]',
        '//audio[@id="audio-source"]',
        '//source[@type="audio/mp3"]',
        '//source[@type="audio/wav"]',
        '//*[@id="audio-source"]',
    ]

    # ── Captcha input XPaths ───────────────────────────
    CAPTCHA_INPUT_XPATHS = [
        '//input[@name="captchaFormLayout$reqstOpenCaptchaTextBox"]',              # BetterDeadCenter
        '//input[contains(@name,"captcha")]',
        '//input[contains(@id,"captcha")]',
        '//input[@id="audio-response"]',            # Google reCAPTCHA
        '//input[contains(@class,"captcha")]',
    ]

    def __init__(self, driver: WebDriver, domain: str = ""):
        """
        Args:
            driver : Selenium WebDriver
            domain : Base domain URL e.g. 'https://portal.city.gov'
                     Used to build full audio URL if relative path given
        """
        self.driver = driver
        self.domain = domain.rstrip("/")
        self.wait   = WebDriverWait(driver, 15)

    # ─────────────────────────────────────────────────
    # MAIN SOLVE
    # ─────────────────────────────────────────────────

    def solve(self) -> bool:
        """
        Full BDC captcha solve flow.

        Returns:
            True if solved, False otherwise
        """
        log.info("🔍 Checking for BDC captcha …")

        if not self._captcha_present():
            log.info("✅ No captcha detected — skipping")
            return True

        log.info("🎯 BDC Captcha detected — solving via audio …")

        try:
            # ── Get audio URL ──────────────────────────
            audio_url = self._get_audio_url()

            if not audio_url:
                log.error("❌ Audio button not found")
                return False

            # ── Build full URL if relative path ────────
            if audio_url.startswith("/"):
                audio_url = self.domain + audio_url
            elif not audio_url.startswith("http"):
                audio_url = self.domain + "/" + audio_url
            elif audio_url.startswith("https"):
                audio_url =audio_url

            log.info(f"🎵 Audio URL: {audio_url}")

            # ── Download audio ─────────────────────────
            audio_path = self._download_audio(audio_url)
            if not audio_path:
                log.error("❌ Audio download failed")
                return False
            # self._save_debug_audio(audio_path)
            # ── Transcribe ─────────────────────────────
            text = self._transcribe_audio(audio_path)
            if not text:
                log.error("❌ Transcription failed")
                return False

            log.info(f"📝 Captcha text: '{text}'")

            # ── Enter solution ─────────────────────────
            success = self._enter_solution(text)

            # ── Cleanup ────────────────────────────────
            self._cleanup(audio_path)

            return success

        except Exception as e:
            log.error(f"❌ Captcha solve error → {e}")
            return False

    # ─────────────────────────────────────────────────
    # CAPTCHA DETECTION
    # ─────────────────────────────────────────────────

    def _captcha_present(self) -> bool:
      """Check if BDC captcha exists on page and scroll to it."""
      for xpath in self.CAPTCHA_PRESENT_XPATHS:
          try:
              # 1. Look for the element in the DOM first
              elements = self.driver.find_elements(By.XPATH, xpath)
              
              if elements:
                  captcha_element = elements[0]
                  
                  # 2. Scroll directly to the exact element using JavaScript
                  # Using {block: 'center'} tries to put the captcha in the middle of the screen
                  self.driver.execute_script(
                      "arguments[0].scrollIntoView({block: 'center'});", 
                      captcha_element
                  )
                  
                  # Give the page a tiny fraction of a second to finish the scroll animation
                  time.sleep(0.5) 
                  
                  log.info(f"🎯 Captcha found and scrolled to: {xpath[:60]}")
                  return True
                  
          except Exception as e:
              # Log the exception if needed, or just continue to the next XPath
              continue
              
      return False

    # ─────────────────────────────────────────────────
    # GET AUDIO URL
    # ─────────────────────────────────────────────────

    def _get_audio_url(self) -> str | None:
        """
        Find the BDC audio/speaker button and get its href URL.

        Returns:
            Audio URL string or None
        """
        for xpath in self.AUDIO_BTN_XPATHS:
            try:
                audio_btn = self.driver.find_element(By.XPATH, xpath)
                audio_url = audio_btn.get_attribute("href")

                if audio_url:
                    log.info(f"🔊 Audio button found: {xpath[:60]}")
                    log.info(f"🔗 Audio href: {audio_url[:80]}")
                    return audio_url

            except NoSuchElementException:
                continue
            except Exception as e:
                log.debug(f"Audio btn error: {e}")
                continue

        log.warning("⚠️  No audio button found with known XPaths")

        # ── Fallback: find any link with BDC in href ───
        try:
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href") or ""
                if "BDC" in href or "captcha" in href.lower() or "sound" in href.lower():
                    log.info(f"🔊 Fallback audio link found: {href[:80]}")
                    return href
        except Exception as e:
            log.debug(f"Fallback audio search error: {e}")

        return None

    # ─────────────────────────────────────────────────
    # DOWNLOAD AUDIO
    # ─────────────────────────────────────────────────

    def _download_audio(self, url: str) -> str | None:
        """
        Download audio file passing browser cookies.

        Returns:
            Local file path or None
        """
        try:
            log.info(f"⬇️  Downloading audio …")

            # ── Pass browser cookies to requests ───────
            cookies = {
                c["name"]: c["value"]
                for c in self.driver.get_cookies()
            }

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": self.driver.current_url,
            }

            response = requests.get(
                url,
                cookies=cookies,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            # ── Detect format ──────────────────────────
            content_type = response.headers.get("Content-Type", "")
            if   "wav"  in content_type: ext = ".wav"
            elif "ogg"  in content_type: ext = ".ogg"
            elif "mpeg" in content_type: ext = ".mp3"
            else:                        ext = ".mp3"

            audio_path = os.path.join(AUDIO_DIR, f"captcha{ext}")

            with open(audio_path, "wb") as f:
                f.write(response.content)

            log.info(f"✅ Audio saved: {audio_path} ({len(response.content)} bytes)")
            return audio_path

        except Exception as e:
            log.error(f"❌ Download error → {e}")
            return None

    # ─────────────────────────────────────────────────
    # TRANSCRIBE AUDIO
    # ─────────────────────────────────────────────────

    def _transcribe_audio(self, audio_path: str) -> str | None:
        """
        Convert audio → text using multiple engines with
        advanced noise reduction and audio preprocessing.
        """
        wav_path     = None
        boosted_path = None
        temp_clean_path = None
        
        try:
            import numpy as np
            import noisereduce as nr
            import soundfile as sf
            from pydub import AudioSegment
            from pydub.scipy_effects import band_pass_filter

            wav_path     = os.path.join(AUDIO_DIR, "captcha.wav")
            boosted_path = os.path.join(AUDIO_DIR, "captcha_boosted.wav")
            temp_clean_path = os.path.join(AUDIO_DIR, "temp_clean.wav")

            log.info("🧹 Removing background noise...")

            # ── Step 1: Spectral Noise Reduction (noisereduce) ──
            # Load the raw audio file as a mathematical array
            data, rate = sf.read(audio_path)
            
            # Convert to mono if the captcha is stereo
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Reduce the stationary background static. 
            # prop_decrease=0.85 means we reduce the noise by 85% to avoid distorting the voice.
            reduced_noise_data = nr.reduce_noise(y=data, sr=rate, prop_decrease=0.85)

            # Save the temporarily denoised audio
            sf.write(temp_clean_path, reduced_noise_data, rate)

            # ── Step 2: Load into Pydub for Frequency Filtering ──
            audio = AudioSegment.from_file(temp_clean_path)

            # ── Step 3: Band-pass Filter (Isolate Voice) ─────────
            # Human voice lives between ~300Hz and ~3400Hz. 
            # This slices off deep rumbles and high-pitched electronic hisses.
            audio = band_pass_filter(audio, 300, 3400)

            # ── Step 4: Format & Boost ───────────────────────────
            audio = audio.set_frame_rate(16000)
            audio = audio + 15  # +15 dB boost to make the isolated voice loud
            audio = audio.normalize()

            # ── Step 5: Add Padding ──────────────────────────────
            silence = AudioSegment.silent(duration=1500)
            audio = silence + audio + silence

            # Export the final pristine audio for Whisper
            audio.export(boosted_path, format="wav")
            log.info(f"✅ Audio cleaned & enhanced — duration: {len(audio)/1000:.1f}s")

            # ── Step 6: Try all engines ──────────────────────────
            result = (
                self._transcribe_whisper(boosted_path)  or
                self._transcribe_google(boosted_path)   or
                self._transcribe_sphinx(boosted_path)
            )

            if result:
                clean = self._clean_captcha_text(result)
                log.info(f"✅ Final captcha text: '{clean}'")
                return clean

            log.error("❌ All transcription engines failed")
            return None

        except Exception as e:
            log.error(f"❌ Transcription error → {e}")
            return None

        finally:
            # Clean up all temporary files
            if temp_clean_path and os.path.exists(temp_clean_path):
                os.remove(temp_clean_path)
            self._cleanup(wav_path, boosted_path)


    def _transcribe_whisper(self, audio_path: str) -> str | None:
        """
        Transcribe using OpenAI Whisper with settings
        optimized for short distorted captcha audio.
        """
        try:
            import whisper

            log.info("🎙️  Trying Whisper transcription …")
            model = whisper.load_model("base")

            for temperature in [0, 0.2, 0.4]:
                try:
                    result = model.transcribe(
                        audio_path,
                        language          = "en",
                        fp16              = False,
                        temperature       = temperature,
                        word_timestamps   = False,
                        condition_on_previous_text = False,
                        # Giving a spaced alphanumeric prompt primes Whisper 
                        # to output individual spaced letters and numbers.
                        initial_prompt    = "A B C 1 2 3.",
                        best_of           = 5,
                        beam_size         = 5,
                    )

                    text = result.get("text", "").strip()
                    if text:
                        log.info(
                            f"✅ Whisper transcribed "
                            f"(temp={temperature}): '{text}'"
                        )
                        return text

                except Exception as e:
                    log.debug(f"Whisper temp={temperature} failed → {e}")
                    continue

            log.warning("⚠️  Whisper returned empty text")
            return None

        except ImportError:
            log.warning("⚠️  Whisper not installed — skipping")
            return None
        except Exception as e:
            log.warning(f"⚠️  Whisper failed → {e}")
            return None


    def _clean_captcha_text(self, text: str) -> str:
        import re
        log.info(f"🧹 Raw transcribed text: '{text}'")

        # 1. Lowercase and remove punctuation (except spaces) to make word boundaries reliable
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', ' ', text)

        # 2. Remove noise phrases
        noise_phrases = [
            "the captcha code is", "captcha code is",
            "the code is", "code is", "please enter",
            "enter", "captcha", "code", "the answer is",
            "answer is", "security code", "type",
        ]
        for phrase in noise_phrases:
            text = text.replace(phrase, " ")

        # 3. Phonetic mapping using exact word boundaries
        word_map = {
            # Numbers
            "zero":"0", "oh":"0",  "one":"1", "won":"1",
            "two":"2",  "to":"2",  "too":"2", "three":"3",
            "four":"4", "for":"4", "or":"4", 
            "five":"5", "six":"6", "seven":"7",
            "eight":"8","ate":"8", "nine":"9","nein":"9",
            # Letters commonly misinterpreted as words by speech engines
            "are": "r", "you": "u", "see": "c", "why": "y",
            "bee": "b", "dee": "d", "gee": "g", "jay": "j",
            "kay": "k", "em": "m", "en": "n", "pea": "p",
            "cue": "q", "queue": "q", "tea": "t", "vee": "v",
            "double u": "w", "double you": "w", "ex": "x"
        }

        # Apply replacements checking for exact words only 
        # (e.g. replaces the word "or", but ignores "or" inside "foreign")
        for word, replacement in word_map.items():
            text = re.sub(rf'\b{word}\b', replacement, text)

        # 4. Finally, strip out all whitespace and non-alphanumeric characters
        text = re.sub(r'[^a-z0-9]', '', text)

        # 5. Return uppercase
        text = text.upper()

        log.info(f"✅ Final captcha text (uppercase): '{text}'")
        return text


    def _transcribe_google(self, wav_path: str) -> str | None:
        """
        Transcribe using Google Speech Recognition API.
        Requires internet connection.
        """
        try:
            log.info("🎙️  Trying Google SR transcription …")
            recognizer                 = sr.Recognizer()
            recognizer.energy_threshold = 200
            recognizer.pause_threshold  = 0.5

            with sr.AudioFile(wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio_data = recognizer.record(source)

            # ── Try with different settings ────────────
            for show_all in [False, True]:
                try:
                    result = recognizer.recognize_google(
                        audio_data,
                        show_all = show_all,
                    )

                    if show_all and isinstance(result, dict):
                        # Get all alternatives and pick best
                        alternatives = (
                            result.get("alternative", [{}])
                        )
                        if alternatives:
                            text = alternatives[0].get("transcript", "")
                            if text:
                                log.info(f"✅ Google SR transcribed: '{text}'")
                                return text
                    elif isinstance(result, str) and result:
                        log.info(f"✅ Google SR transcribed: '{result}'")
                        return result

                except sr.UnknownValueError:
                    continue

            log.warning("⚠️  Google SR could not understand audio")
            return None

        except sr.RequestError as e:
            log.warning(f"⚠️  Google SR API error → {e}")
            return None
        except Exception as e:
            log.warning(f"⚠️  Google SR failed → {e}")
            return None


    def _transcribe_sphinx(self, wav_path: str) -> str | None:
        """
        Transcribe using CMU Sphinx (offline fallback).
        Works without internet.
        """
        try:
            log.info("🎙️  Trying Sphinx transcription …")
            recognizer = sr.Recognizer()

            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)

            text = recognizer.recognize_sphinx(audio_data)
            if text:
                log.info(f"✅ Sphinx transcribed: '{text}'")
                return text

            return None

        except ImportError:
            log.warning("⚠️  Sphinx not installed — skipping")
            return None
        except Exception as e:
            log.warning(f"⚠️  Sphinx failed → {e}")
            return None


    # def _clean_captcha_text(self, text: str) -> str:
    #     """
    #     Clean transcribed text to get pure captcha code.

    #     Removes:
    #       - Spaces
    #       - Punctuation
    #       - Common speech artifacts
    #       - Extra words spoken around the code
    #     """
    #     import re

    #     log.info(f"🧹 Cleaning raw text: '{text}'")

    #     # ── Lowercase ──────────────────────────────────
    #     text = text.lower().strip()

    #     # ── Remove common speech artifacts ────────────
    #     noise_words = [
    #         "please enter", "enter", "type", "captcha",
    #         "code is", "the code", "code", "is", "please",
    #         "security", "characters", "character",
    #     ]
    #     for word in noise_words:
    #         text = text.replace(word, "")

    #     # ── Keep only alphanumeric characters ─────────
    #     text = re.sub(r'[^a-z0-9]', '', text)

    #     # ── Common audio mishearing fixes ─────────────
    #     replacements = {
    #         "zero" : "0",
    #         "one"  : "1",
    #         "two"  : "2",
    #         "three": "3",
    #         "four" : "4",
    #         "five" : "5",
    #         "six"  : "6",
    #         "seven": "7",
    #         "eight": "8",
    #         "nine" : "9",
    #         "oh"   : "0",
    #         "i"    : "1",
    #         "l"    : "1",
    #         "o"    : "0",
    #     }
    #     for word, replacement in replacements.items():
    #         text = text.replace(word, replacement)

    #     log.info(f"✅ Cleaned captcha text: '{text}'")
    #     return text

    # ─────────────────────────────────────────────────
    # ENTER SOLUTION
    # ─────────────────────────────────────────────────

    def _enter_solution(self, text: str) -> bool:
        """
        Type transcribed text into BDC captcha input box.

        Returns:
            True if typed successfully
        """
        for xpath in self.CAPTCHA_INPUT_XPATHS:
            try:
                input_el = self.driver.find_element(By.XPATH, xpath)
                input_el.clear()
                input_el.send_keys(text)
                log.info(f"✅ Captcha answer entered: '{text}'")
                time.sleep(0.3)
                return True
            except NoSuchElementException:
                continue
            except Exception as e:
                log.debug(f"Input error: {e}")
                continue

        log.error("❌ Captcha input field not found")
        return False

    # ─────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────

    def _cleanup(self, *paths) -> None:
        """Delete temp audio files."""
        for path in paths:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
                    log.debug(f"🗑️  Deleted: {path}")
            except Exception:
                pass
    def _save_debug_audio(self, audio_path: str) -> None:
        """
        Copy audio to a fixed debug location so you can
        listen to it manually to verify transcription.
        """
        try:
            import shutil
            debug_path = "debug_captcha_audio.mp3"
            shutil.copy2(audio_path, debug_path)
            log.info(f"🐛 Debug audio saved → {debug_path}")
            log.info("    Listen to this file to verify what the captcha says")
        except Exception as e:
            log.debug(f"Debug audio save failed → {e}")