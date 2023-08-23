import random
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Meant to be the final function called in the chain
# Closes the driver, returns the cookies and user agent
def _get_cookies(driver):
    cookies = driver.get_cookies()
    user_agent = driver.execute_script("return navigator.userAgent;")
    driver.quit()
    return {
        "cookies": cookies,
        "user_agent": user_agent
    }

# Checks if the captcha is present on the page
# by checking if the page loaded the endpoint correctly
def _check_captcha_presence(driver):
    return driver.execute_script("return !document.body.textContent.includes('calendarSelectableDays');")

# Moves the mouse around
def _move_mouse_randomly(driver, actions):
    # Move to a fixed point in the top left corner of the screen
    actions.move_to_element_with_offset(driver.find_element(By.TAG_NAME, 'body'), 20, 20).perform()

    # Move the mouse towards the center of the screen-ish
    for _ in range(10):
        offset_x = random.randint(-1, 10)
        offset_y = random.randint(-1, 10)
        actions.move_by_offset(offset_x, offset_y).perform()
        time.sleep(random.uniform(0.05, 0.15))

# Solves captcha by means of sending keypresses
def _solve_captcha(actions):
    # Send a tab key to focus the captcha
    actions.send_keys(Keys.TAB)
    actions.perform()

    # wait a random amount of time between 1.00 and 3.00 seconds
    time.sleep(random.uniform(1.00, 3.00))

    # Hold down the Enter or space key for 10 seconds to submit the captcha
    key = random.choice([Keys.ENTER, Keys.SPACE])
    actions.key_down(key).perform()
    time.sleep(10)
    actions.key_up(key).perform()

# Entry function for the module
# This will navigate to one of the Frontier endpoints
# and attempt to bypass the captcha by means of
# simulating human-like behavior (mouse movements, tabbing, etc.)
# It will then use tab/enter to submit the captcha
# Each attempt takes about 25-30 seconds to complete
# If it fails, it will retry a few times before giving up
def get_cookies(retries=3):

    # Options to disable automation detection
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Create the driver
    driver = webdriver.Chrome(options=options)

    # Navigate to the endpoint using a dummy URL
    driver.get("https://booking.flyfrontier.com/Flight/RetrieveSchedule?calendarSelectableDays.Origin=MCI&calendarSelectableDays.Destination=DEN")

    # Wait a generic five seconds for page to load
    # Hard to detect when captcha is loaded, because of the intense frame nesting
    time.sleep(5)

    # Check whether captcha is present, if not,
    # Lets use this session's information for further automation
    if not _check_captcha_presence(driver):
        return _get_cookies(driver)

    # Create ActionChains instance for simulating movements/keystrokes
    actions = ActionChains(driver)

    # Move the mouse around randomly for 10 seconds
    _move_mouse_randomly(driver, actions)

    # Simulate pressing the Tab key
    _solve_captcha(driver, actions)

    # Now, once the captcha has been solved,
    # It can take some time before it allows us to continue
    # We will wait a generic amount of time for the page to load
    time.sleep(10)

    # Check if loaded successfully
    if not _check_captcha_presence(driver):
        return _get_cookies(driver)
    
    # If we get here, something went wrong
    # We will retry the process a few times
    # before giving up
    if retries > 1:
        return get_cookies(retries - 1)
    else:
        raise Exception("Failed to solve captcha")