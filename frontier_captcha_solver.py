import random
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import json

from selenium.webdriver.chrome.options import Options

def _get_cookies(driver):
    cookies = driver.get_cookies()
    user_agent = driver.execute_script("return navigator.userAgent;")
    driver.quit()
    return {
        "cookies": cookies,
        "user_agent": user_agent
    }

def get_cookies():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    driver.get("https://booking.flyfrontier.com/Flight/RetrieveSchedule?calendarSelectableDays.Origin=MCI&calendarSelectableDays.Destination=DEN")

    # wait 5 seconds using system methods
    time.sleep(6)

    # Check if loaded successfully
    no_captcha = driver.execute_script("return document.body.textContent.includes('calendarSelectableDays');")
    if no_captcha:
        print("No captcha detected")
        return _get_cookies(driver)

    # Get the screen's dimensions
    #screen_width, screen_height = driver.execute_script("return [window.innerWidth, window.innerHeight]")

    # Create ActionChains instance
    actions = ActionChains(driver)

    # Determine the center of the screen
    #center_x, center_y = screen_width // 2, screen_height // 2

    # Move to a random position near the center
    #start_x, start_y = center_x + random.randint(-100, 100), center_y + random.randint(-100, 100)
    actions.move_to_element_with_offset(driver.find_element(By.TAG_NAME, 'body'), 20, 20).perform()

    # Move randomly around the center of the screen
    for _ in range(10): # Adjust the range for more/less movements
        offset_x = random.randint(-1, 10)
        offset_y = random.randint(-1, 10)
        actions.move_by_offset(offset_x, offset_y).perform()

    # Simulate pressing the Tab key
    actions = ActionChains(driver)
    actions.send_keys(Keys.TAB)
    actions.perform()

    # wait a random amount of time between 1.00 and 3.00 seconds
    time.sleep(random.uniform(1.00, 3.00))

    # Hold down the Enter key for 10 seconds
    actions = ActionChains(driver)
    actions.key_down(Keys.ENTER).perform()
    time.sleep(10)
    actions.key_up(Keys.ENTER).perform()

    time.sleep(10)

    # Check if loaded successfully
    no_captcha = driver.execute_script("return document.body.textContent.includes('calendarSelectableDays');")
    if no_captcha:
        print("No captcha detected. Captcha bypassed!")
        return _get_cookies(driver)
    
    print("unknown error occurred")
    
    driver.quit()
    return None

print(get_cookies())