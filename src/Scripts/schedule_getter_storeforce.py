from src.config.DRIVER_CACHE_DIRECTORY import CACHE_DIR
from src.config.LUSH_STORE_FORCE_URL import URL
from src.config.CREDENTIALS import ARI_USER, ARI_PASS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(path=CACHE_DIR).install()))

driver.get(URL)

inputs_locator = driver.find_element(By.ID, 'login-inputs-container')
login_btn = driver.find_element(By.TAG_NAME, 'Button')

user_in = inputs_locator.find_element(By.CSS_SELECTOR, '[type="text"]')
pass_in = inputs_locator.find_element(By.CSS_SELECTOR, '[type="password"]')

user_in.send_keys(ARI_USER)
pass_in.send_keys(ARI_PASS)
login_btn.click()

driver.quit()
