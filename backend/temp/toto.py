import os
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium import webdriver

import time

from backend import PROJECT_PATHS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('automation.log')
    ]
)
logger = logging.getLogger('automation')

# Set up the WebDriver
# driver = webdriver.Chrome()  # Specify path if needed: executable_path='/path/to/chromedriver'
# driver.maximize_window()  # Set window size similar to original session
# 

try:
    # Initial page load
    logger.info("Setting up Chrome options...")
    options = Options()
    options.add_argument("--start-maximized")
    
    # Add user data directory to persist profile data
    user_data_dir = os.path.join(PROJECT_PATHS.RAW_DATA, 'chrome_profile')
    options.add_argument(f'--user-data-dir={user_data_dir}')
    options.add_argument('--profile-directory=Default')
    
    # Additional useful options
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_argument('--password-store=basic')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Disable automation info bars
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    logger.info("Initializing Chrome driver...")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    logger.info("Navigating to HeySam website...")
    driver.get("https://www.heysam.ai/")
    time.sleep(1)

    # 1. Hover over the Login button
    logger.info("Looking for Login button...")
    login_button = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@class='buttonprimary w-nav-link']")))
    logger.info("Hovering over Login button...")
    actions = ActionChains(driver)
    actions.move_to_element(login_button).perform()
    time.sleep(1)
    breakpoint()
    # 2. Click the Login button (navigates to app.heysam.ai)
    logger.info("Clicking Login button...")
    login_button.click()
    time.sleep(1)  # Wait for navigation
    logger.info("Successfully navigated to app page")

    # 3. On the app page, move cursor to different elements
    # This is just mouse movement, no specific action needed
    # time.sleep(2)

    # 4. Hover over the recordings icon in the sidebar
    logger.info("Looking for recordings button in sidebar...")
    recordings_button = wait.until(EC.presence_of_element_located((By.XPATH, "//aside[contains(@class, 'flex flex-col justify-between')]/div[contains(@class, 'flex flex-col gap-2')]/div[2]/button")))
    logger.info("Hovering over recordings button...")
    actions.move_to_element(recordings_button).perform()
    time.sleep(1)

    # 5. Click on the recordings icon
    logger.info("Clicking recordings button...")
    recordings_button.click()
    time.sleep(1)  # Wait for navigation to recordings page
    logger.info("Successfully navigated to recordings page")

    # 6. Find and click on a specific recording (Adil/Katie recording)
    logger.info("Looking for Adil/Katie recording...")
    recording_element = wait.until(EC.presence_of_element_located((By.XPATH, "//strong[contains(text(), 'Adil (HeySam) / Katie')]")))
    logger.info("Hovering over recording element...")
    actions.move_to_element(recording_element).perform()
    time.sleep(1)
    logger.info("Clicking on recording...")
    recording_element.click()
    time.sleep(1)  # Wait for recording page to load
    logger.info("Successfully opened recording")

    # 7. Click on the "Discovery Checklist" tab
    logger.info("Looking for Discovery Checklist tab...")
    discovery_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Discovery Checklist')]")))
    logger.info("Clicking Discovery Checklist tab...")
    discovery_tab.click()
    time.sleep(1)
    logger.info("Successfully switched to Discovery Checklist")

    # # 8. Click on the question about Sales Engineers
    # logger.info("Looking for Sales Engineers question...")
    # se_question = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='radix-:r6c:']")))
    # logger.info("Hovering over Sales Engineers question...")
    # actions.move_to_element(se_question).perform()
    # time.sleep(1)
    # logger.info("Clicking Sales Engineers question...")
    # se_question.click()
    # time.sleep(1)
    # logger.info("Successfully expanded Sales Engineers question")

    # # 9. Click on the question about recording demos
    # logger.info("Looking for recording demos question...")
    # demos_question = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@id='radix-:r6k:']")))
    # logger.info("Hovering over recording demos question...")
    # actions.move_to_element(demos_question).perform()
    # time.sleep(1)
    # logger.info("Clicking recording demos question...")
    # demos_question.click()
    # time.sleep(1)
    # logger.info("Successfully expanded recording demos question")

    # # 10. Scroll down to see more content
    # logger.info("Scrolling down the page...")
    # driver.execute_script("window.scrollBy(0, 500);")
    # time.sleep(1)

    # 11. Click on the graduation cap icon for learning
    logger.info("Looking for graduation cap icon...")
    grad_cap = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@class='lucide lucide-graduation-cap stroke-white shrink-0']")))
    logger.info("Hovering over graduation cap icon...")
    actions.move_to_element(grad_cap).perform()
    time.sleep(1)
    logger.info("Clicking graduation cap icon...")
    grad_cap.click()
    time.sleep(1)
    logger.info("Successfully opened learning panel")

    # 12. Click on "Sizzle reel"
    logger.info("Looking for Sizzle reel option...")
    sizzle_reel = wait.until(EC.element_to_be_clickable((By.XPATH, "//p[contains(text(), 'Sizzle reel')]")))
    logger.info("Hovering over Sizzle reel option...")
    actions.move_to_element(sizzle_reel).perform()
    time.sleep(1)
    logger.info("Clicking Sizzle reel option...")
    sizzle_reel.click()
    time.sleep(1)
    logger.info("Successfully opened Sizzle reel")

    # 13. Final mouse movements exploring the page
    logger.info("Performing exploratory mouse movements...")
    for i in range(3):
        logger.info(f"Exploratory movement {i+1}/3")
        actions.move_by_offset(200, 100).perform()
        time.sleep(1)
        actions.move_by_offset(-100, 200).perform()
        time.sleep(1)

    logger.info("Automation completed successfully")

except Exception as e:
    logger.error(f"An error occurred: {e}", exc_info=True)
    print(f"Automation failed. See log for details.")

finally:
    # Keep the browser open for a few seconds before closing
    logger.info("Waiting 5 seconds before closing browser...")
    time.sleep(5)
    logger.info("Closing browser")
    driver.quit()