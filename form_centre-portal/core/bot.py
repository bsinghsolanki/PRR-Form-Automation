from data.google_sheet import load_rows, update_status
from engine.field_detector import build_form_map
from engine.form_filler import fill_form, select_email_delivery
from driver.browser import get_driver, open_portal

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from engine.discovery_runner import FormScraper
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import time

class FormBot:

    def __init__(self, credentials, sheet_id, worksheet):

        self.credentials = credentials
        self.sheet_id    = sheet_id
        self.worksheet   = worksheet

        self.rows = load_rows(credentials, sheet_id, worksheet)

        self.driver = None
        self.wait   = None


    def get_portal_url(self, row):
        for key in row.keys():
            if key.lower() == "portal url":
                return row[key]
        return None


    def run(self):

        for idx, row in enumerate(self.rows, start=1):

            print(f"\n========== ROW {idx} | {row.get('agency name', '')} ==========")

            self.driver = get_driver()
            self.wait   = WebDriverWait(self.driver, 25)

            url    = self.get_portal_url(row)
            status = "Not Filled"
            error  = ""

            try:
                if not url:
                    raise ValueError("No portal URL found in row")

                print(f"🚀 Opening: {url}")

                open_portal(self.driver, url)

                form_map = build_form_map(self.driver)

                fill_form(
                    driver=self.driver,
                    row=row,
                    form_map=form_map,
                )

                select_email_delivery(self.driver, email_value=row.get("email", ""))

                input("Solve captcha -> press ENTER")

                # ── Uncomment when ready to auto-submit ──────────────────
                status = "Not Filled"
                max_pages = 10  # Failsafe to prevent infinite loops
                short_wait = WebDriverWait(self.driver, 3)  # 3-second wait so it checks quickly

                for step in range(max_pages):
                    try:
                        # 1. Check if the final Submit button is present
                        submit_btn = short_wait.until(
                            EC.element_to_be_clickable((By.ID, "btnFormSubmit"))
                        )
                        self.driver.execute_script("arguments[0].click();", submit_btn)
                        
                        status = "Filled"
                        print(f"✅ FORM SUBMITTED — {row.get('agency name', url)}")
                        break  # We clicked Submit! Break out of the loop completely.

                    except TimeoutException:
                        # 2. If Submit isn't there, look for the Continue button
                        try:
                            continue_btn = short_wait.until(
                                EC.element_to_be_clickable((By.XPATH, '//ol[@class="selfClear cpForm"]//span[contains(text(),"Continue")]'))
                            )
                            self.driver.execute_script("arguments[0].click();", continue_btn)
                            print(f"➡️ Clicked 'Continue' (Step {step + 1}). Loading next section...")
                            
                            # Wait a moment for the transition/next page to load
                            time.sleep(2) 
                            
                        except TimeoutException:
                            # 3. If neither Submit nor Continue is found, something is wrong
                            status = "Not Filled"
                            print(f"❌ BOT ERROR: Neither 'Submit' nor 'Continue' found on step {step + 1}.")
                            break
                            
                    except Exception as e:
                        # Catch any other unexpected UI errors (like stale elements)
                        status = "Not Filled"
                        print(f"❌ BOT ERROR: {str(e)}")
                        break
                else:
                    # 4. If the loop hits max_pages without ever breaking, it stops itself
                    status = "Not Filled"
                    print(f"❌ BOT ERROR: Stuck in a loop? Reached {max_pages} pages without finding a Submit button.")

            finally:
                # Always log to Sheet2 regardless of success or failure
                update_status(
                    credentials_file=self.credentials,
                    sheet_id=self.sheet_id,
                    row_data=row,
                    status=status,
                    error=error,
                )

                try:
                    self.driver.quit()
                except Exception:
                    pass