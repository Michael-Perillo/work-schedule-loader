import datetime as dt
import os
import time
from typing import Tuple, Dict
from src.config.DRIVER_CACHE_DIRECTORY import CACHE_DIR
from src.config.LUSH_STORE_FORCE_URL import URL
from src.Classes.work_shift import WorkShift
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


def parse_workday_shift_string(workday_shift_string: str) -> Tuple[dt.time, dt.time]:
    workday_shift_range_strings = [shift.strip() for shift in workday_shift_string.split('-')]
    start_time, end_time = dt.datetime.strptime(workday_shift_range_strings[0], "%I:%M %p").time(), dt.datetime.strptime(workday_shift_range_strings[1], "%I:%M %p").time()
    return start_time, end_time


def send_data(input_box: webdriver, _in: str, timeout: int) -> bool:
    count = 0
    while input_box.get_attribute('value') != _in:
        if count > timeout:
            return False
        input_box.send_keys(_in)
        count += 1
        time.sleep(1)
    return True


def get_schedule_dict_for_user(user_in: str, user_pass: str) -> Dict[str, WorkShift]:
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(path=CACHE_DIR).install()))
    driver.implicitly_wait(10)
    driver.get(URL)

    inputs_locator = driver.find_element(By.ID, 'login-inputs-container')
    login_btn = driver.find_element(By.TAG_NAME, 'Button')

    user_in_box = inputs_locator.find_element(By.CSS_SELECTOR, '[type="text"]')
    pass_in_box = inputs_locator.find_element(By.CSS_SELECTOR, '[type="password"]')

    LOGIN_TIMEOUT = 10
    user_in_box.send_keys(user_in)
    WebDriverWait(driver, LOGIN_TIMEOUT).until(lambda driver: send_data(user_in_box, user_in, LOGIN_TIMEOUT))
    pass_in_box.send_keys(user_pass)
    WebDriverWait(driver, LOGIN_TIMEOUT).until(lambda driver: send_data(pass_in_box, user_pass, LOGIN_TIMEOUT))
    login_btn.click()

    menu_buttons = driver.find_element(By.ID, 'buttons')
    schedule_btn = menu_buttons.find_element(By.CSS_SELECTOR, '[data-bind="click: ScheduleClicked"]')
    schedule_btn.click()

    schedule_calendar = driver.find_element(By.ID, 'scheduleContent')
    week_tbody = schedule_calendar.find_element(By.CSS_SELECTOR, '[data-bind="foreach: ScheduleWeeks"]')
    month = dt.datetime.strptime(schedule_calendar.find_element(By.CSS_SELECTOR, '[data-bind="text: MonthName"]').text,
                                 "%B").month
    today = dt.datetime.today().date()
    assert today.month == month
    weeks = week_tbody.find_elements(By.TAG_NAME, 'tr')

    sched_dict = {}
    for week in weeks:
        days = week.find_elements(By.TAG_NAME, 'td')
        for index, day in enumerate(days):
            try:
                workday_str = day.text
                if len(workday_str) <= 1:
                    continue
                workday_info = workday_str.split('\n')
                workday_numeric_day = int(workday_info[0])
                if workday_numeric_day < today.day:
                    continue
                workday_shift_string = workday_info[-1]
                workday_shift_start, workday_shift_end = parse_workday_shift_string(workday_shift_string)
                workday_date = dt.datetime(today.year, today.month, workday_numeric_day).date()
                work_shift = WorkShift(workday_date, workday_shift_start, workday_shift_end)
                sched_dict[workday_date.strftime('%Y%m%d')] = work_shift
            except Exception:
                continue
    driver.quit()
    return sched_dict




