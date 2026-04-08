import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Import your custom modules
from engine.field_detector import build_form_map

# --- HELPER FUNCTIONS ---

def get_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # options.add_argument("--headless=new") # Uncomment for server
    return webdriver.Chrome(options=options)

def open_portal(driver, url, timeout=10):
    wait = WebDriverWait(driver, timeout)
    driver.get(url)
    time.sleep(5)
    try:
        # ✅ Try direct form load detection
        # wait.until(
        #     EC.presence_of_element_located((By.XPATH, '//div[@id="formWrap"] | //form'))
        # )
        continue_btn = wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='wizardTop']//span[normalize-space()='Continue'] | //button[contains(.,'Continue')]"))
            )
        driver.execute_script("arguments[0].click();", continue_btn)
        time.sleep(3) # Wait for animation
        print("✅ Form loaded after Continue")
    except:
        print("⚠️ Form not visible — checking for Continue button...")
        try:
          wait.until(
            EC.presence_of_element_located((By.XPATH, '//div[@id="formWrap"] | //form'))
            )
            # Check for that specific span inside the wizard buttons
        except Exception as e:
            print(f"❌ No form or continue button found at {url}")
            return False
    return True

# --- MAIN SCRAPER CLASS ---
import pandas as pd

# def save_pivoted_csv(scraped_data_list, output_file="form_summary_horizontal.csv"):
#     """
#     scraped_data_list: list of dicts from your scraper
#     [{'URL': '...', 'Label': 'first name', 'Type': 'text', ...}]
#     """
#     # 1. Convert list to DataFrame
#     df = pd.DataFrame(scraped_data_list)

#     # 2. Create a unique column name by combining Label + Info
#     # Example: "first name (Type)" and "first name (Options)"
    
#     # We pivot so each URL is one row
#     pivot_df = df.pivot(index='URL', columns='Label', values=['Type', 'Options', 'Full_Context_Text'])
    
#     # 3. Flatten the multi-level columns into something readable like "first name_Type"
#     pivot_df.columns = [f"{col[1]}_{col[0]}" for col in pivot_df.columns]
    
#     # 4. Save to CSV
#     pivot_df.to_csv(output_file)
#     print(f"✨ Horizontal Summary saved to {output_file}")

import pandas as pd
import csv
# from driver.browser import get_driver, open_portal
from engine.field_detector import build_form_map
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By

class FormScraper:
    def __init__(self, urls):
        self.urls = urls
        self.output_file = "form_matrix_summary.csv"

    def run_discovery(self):
        driver = get_driver()
        all_data = []

        for url in self.urls:
            print(f"🔍 Investigating: {url}")
            try:
                if not open_portal(driver, url):
                    continue
                
                # Inside your run_discovery method, after build_form_map(driver):

                form_map = build_form_map(driver)
                print(f"📊 Detected {len(form_map)} fields on page.")

                for label, meta in form_map.items():
                    options = []
                    
                    # --- 1. Aggressive Option Extraction for Radios/Checkboxes ---
                    if meta["type"] in ["radio", "checkbox"]:
                        # meta["element"] is a list for these types
                        elements = meta["element"] if isinstance(meta["element"], list) else [meta["element"]]
                        for el in elements:
                            try:
                                # Try getting the label text linked to this specific radio/checkbox
                                opt_id = el.get_attribute('id')
                                if opt_id:
                                    # Look for <label for="id">
                                    lbl_element = driver.find_element(By.XPATH, f"//label[@for='{opt_id}']")
                                    options.append(lbl_element.text.strip())
                            except:
                                # Fallback: Check if the text is inside the parent or a sibling
                                try:
                                    options.append(el.find_element(By.XPATH, "..").text.strip())
                                except:
                                    options.append("Option-Text-Missing")

                    # --- 2. Build the row for this specific field ---
                    field_data = {
                        "URL": url,
                        "Label": label,
                        "Type": meta["type"],
                        "Options": " | ".join(options) if options else "N/A",
                        "Context": meta.get("full_text", "").replace("\n", " ")
                    }
                    
                    # --- 3. Append to your master list ---
                    all_data.append(field_data)
                    print(f"✅ Added: {label}") # Debugging line

            except Exception as e:
                print(f"⚠️ Error on {url}: {e}")

        driver.quit()

        # --- PIVOT LOGIC WITH DEDUPLICATION ---
        if all_data:
            df = pd.DataFrame(all_data)
            
            # 1. REMOVE DUPLICATES: 
            # This keeps only one 'first name' per URL
            df = df.drop_duplicates(subset=['URL', 'Label'], keep='first')

            # 2. NOW PIVOT:
            pivot_df = df.pivot(index='URL', columns='Label', values=['Type', 'Options'])
            
            # 3. CLEAN HEADERS:
            pivot_df.columns = [f"{col[1]} ({col[0]})" for col in pivot_df.columns]
            
            pivot_df.to_csv(self.output_file)
            print(f"✨ Horizontal Summary saved to {self.output_file}")
# --- EXECUTION ---

# if __name__ == "__main__":
#     # Define your list of URLs here
#     # my_urls = [
#     #     "https://www.example.gov/opra-portal-url", 
#     # ]
    
#     scraper = FormScraper(urls=my_urls)
#     scraper.run_discovery()