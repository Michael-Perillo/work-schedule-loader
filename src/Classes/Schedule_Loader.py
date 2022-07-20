import datetime as dt
import time
import logging
from typing import Tuple, Dict
from src.config.DRIVER_CACHE_DIRECTORY import CACHE_DIR
from src.config.LUSH_STORE_FORCE_URL import URL
from src.Classes.work_shift import WorkShift
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


class ScheduleLoader(object):
    def __init__(self, user_in: str, user_pass: str, timeout: int):
        self.user_in = user_in
        self.user_pass = user_pass
        self.timeout = timeout
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(path=CACHE_DIR).install()))
        self.schedule_dict = self.load_schedule()
        self.driver.quit()

    def wait_to_find_element(self, driver: webdriver) -> webdriver:
        wait = WebDriverWait(driver, timeout=self.timeout)
        return wait.until(EC.visibility_of(driver))

    def login(self, user_box: webdriver, pass_box: webdriver, login_btn: webdriver) -> bool:
        user_input_check = EC.text_to_be_present_in_element_value(user_box, self.user_in)
        pass_input_check = EC.text_to_be_present_in_element_value(pass_box, self.user_pass)
        check_inputs = EC.all_of(user_input_check, pass_input_check)
        timeout_delta = dt.timedelta(seconds=self.timeout)
        start_time = time.clock()
        run_time = dt.timedelta(seconds=0)
        while (not check_inputs or (timeout_delta > run_time)):
            user_box.send_keys(self.user_in)
            pass_box.send_keys(self.user_pass)
            user_input_check = EC.text_to_be_present_in_element_value(user_box, self.user_in)
            pass_input_check = EC.text_to_be_present_in_element_value(pass_box, self.user_pass)
            check_inputs = EC.all_of(user_input_check, pass_input_check)
            run_time = time.clock() - start_time
        if check_inputs:
            login_btn.click()
            return True
        else:
            return False

    def parse_weeks(self, weeks: webdriver):
        sched_dict = {}
        today = dt.datetime.today()
        for week in weeks:
            # TODO: Refactor this to work with self.wait_until_element_found, this returns a list
            days = WebDriverWait(week, timeout=5).until(lambda d: d.find_elements(By.TAG_NAME, 'td'))
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
                    workday_shift_start, workday_shift_end = self.parse_workday_shift_string(workday_shift_string)
                    workday_date = dt.datetime(today.year, today.month, workday_numeric_day).date()
                    work_shift = WorkShift(workday_date, workday_shift_start, workday_shift_end)
                    sched_dict[workday_date.strftime('%Y%m%d')] = work_shift
                except Exception:
                    continue
        return sched_dict

    @staticmethod
    def parse_workday_shift_string(workday_shift_string: str) -> Tuple[dt.time, dt.time]:
        workday_shift_range_strings = [shift.strip() for shift in workday_shift_string.split('-')]
        start_time, end_time = dt.datetime.strptime(workday_shift_range_strings[0],
                                                    "%I:%M %p").time(), dt.datetime.strptime(
            workday_shift_range_strings[1], "%I:%M %p").time()
        return start_time, end_time

    def load_schedule(self) -> Dict[str, WorkShift]:
        self.driver.get(URL)

        inputs_locator = self.wait_to_find_element(self.driver.find_element(By.ID, 'login-inputs-container'))
        login_btn = self.wait_to_find_element(self.driver.find_element(By.TAG_NAME, 'Button'))
        username_box = self.wait_to_find_element(inputs_locator.find_element(By.CSS_SELECTOR, '[type="text"]'))
        password_box = self.wait_to_find_element(inputs_locator.find_element(By.CSS_SELECTOR, '[type="password"]'))

        logged_in = self.login(username_box, password_box, login_btn)

        if logged_in:
            schedule_btn = self.wait_to_find_element(self.driver.find_element(By.CSS_SELECTOR,
                                                                              '[data-bind="click: ScheduleClicked"]'))
            schedule_btn.click()
            self.wait_to_find_element(self.driver.find_element(By.CSS_SELECTOR, '[data-bind="foreach: ScheduleWeeks"]'))
            weeks = self.wait_to_find_element(self.driver.find_element(By.TAG_NAME, 'tr'))
            return self.parse_weeks(weeks)
        else:
            logging.error(f"Unable to log in for user {self.user_in}, please retry with a higher timeout or check logic")

