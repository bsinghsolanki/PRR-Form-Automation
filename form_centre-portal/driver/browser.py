from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import TimeoutException

def get_driver():

    options = Options()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # Uncomment for server
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    return driver


# ⭐ PRODUCTION PORTAL LOADER
def open_portal(driver, url, timeout=30):

    wait = WebDriverWait(driver, timeout)
    driver.get(url)

    try:
        # ✅ Wait for either form OR continue button
        wait.until(
            EC.any_of(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@id="formWrap"]//input[@type="text"]')
                ),
                EC.presence_of_element_located(
                    (By.XPATH, "//span[normalize-space()='Continue']")
                )
            )
        )

        print("🔍 Page loaded, checking flow...")

        # 🔹 If Continue button exists → click it
        try:
            continue_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//span[normalize-space()='Continue']")
                )
            )
            driver.execute_script("arguments[0].click();", continue_btn)
            print("✅ Clicked Continue")

        except TimeoutException:
            print("✅ Form loaded directly")

        # 🔹 Now wait for actual form input
        try:
            wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//div[@id="formWrap"]//input[@type="text"]')
                )
            )
        except:
            wait.until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="formWrap"]//input[@type="text"]'))
            )
        print("✅ Form is visible")

        # 🔹 Handle popup if present
        try:
            close_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//div[@role="dialog"]//button[contains(@class,"cp-Splash-Btn--Close")]')
                )
            )
            close_btn.click()
            print("✅ Popup closed")

        except TimeoutException:
            pass

    except TimeoutException:
        raise Exception("❌ Portal opened but form not detected.")
