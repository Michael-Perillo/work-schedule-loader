import datetime as dt
import time
import logging
from typing import Tuple, Dict, List
from src.config.DRIVER_CACHE_DIRECTORY import CACHE_DIR
from src.config.LUSH_STORE_FORCE_URL import URL
from src.Classes.work_shift import WorkShift
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import copy
import re


class ScheduleLoader(object):
    def __init__(self, user_in: str, user_pass: str, timeout: int):
        self.user_in = user_in
        self.user_pass = user_pass
        self.timeout = timeout
        self.date = dt.date.today()
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager(path=CACHE_DIR).install()))
        self.schedule_dict = self.load_schedule()
        self.driver.quit()

    def wait_to_find(self, condition: EC) -> WebDriver:
        wait = WebDriverWait(self.driver, timeout=self.timeout)
        return wait.until(condition)

    def login(self, user_box: webdriver, pass_box: webdriver, login_btn: webdriver) -> bool:
        start_time = time.perf_counter()
        run_time = 0
        while self.timeout > run_time:
            user_box.send_keys(self.user_in)
            time.sleep(.25)
            pass_box.send_keys(self.user_pass)
            time.sleep(.25)
            try:
                login_btn.click()
                WebDriverWait(self.driver, 10).until(lambda d: d.find_element(By.ID, 'buttons').find_element(By.CSS_SELECTOR, '[data-bind="click: ScheduleClicked"]'))
                return True
            except TimeoutException:
                run_time = time.perf_counter() - start_time
                self.driver.find_element(By.ID, 'btnMessageBoxClose').click()
                user_box.clear()
                pass_box.clear()
                continue
        return False

    def parse_scheduled_days(self, schedule: List[List[BeautifulSoup]]) -> Dict[str, WorkShift]:
        out_dict = {}
        for index, month_sched_days in enumerate(schedule):
            if not index:
                month = self.date.month
            else:
                month = self.date.month + 1
            for day in month_sched_days:
                shift_day_numeric = int(day.find_next('label', attrs={'data-bind': re.compile("Day$")}).text)
                if shift_day_numeric <= self.date.day and month == self.date.month:
                    continue
                else:
                    shift_hours_raw = day.find_next('label', attrs={'data-bind': re.compile("Shift$")}).text
                    shift_start, shift_end = self.parse_workday_shift_string(shift_hours_raw)
                    shift_date = dt.date(self.date.year, month, shift_day_numeric)
                    out_dict[shift_date.strftime('%Y%m%d')] = WorkShift(shift_date, shift_start, shift_end)
        return out_dict

    @staticmethod
    def parse_workday_shift_string(workday_shift_string: str) -> Tuple[dt.time, dt.time]:
        workday_shift_range_strings = [shift.strip() for shift in workday_shift_string.split('-')]
        start_time, end_time = dt.datetime.strptime(workday_shift_range_strings[0],
                                                    "%I:%M %p").time(), dt.datetime.strptime(
            workday_shift_range_strings[1], "%I:%M %p").time()
        return start_time, end_time

    def load_schedule(self) -> Dict[str, WorkShift]:
        self.driver.get(URL)

        # inputs_locator = (By.ID, 'login-inputs-container')
        login_btn_locator = (By.TAG_NAME, 'Button')
        user_box_locator = (By.CSS_SELECTOR, '[type="text"]')
        pass_box_locator = (By.CSS_SELECTOR, '[type="password"]')
        self.wait_to_find(EC.presence_of_element_located(login_btn_locator))
        self.wait_to_find(EC.presence_of_element_located(user_box_locator))
        self.wait_to_find(EC.presence_of_element_located(pass_box_locator))


        inputs_location = self.driver.find_element(By.ID, 'login-inputs-container')
        login_btn = self.driver.find_element(By.TAG_NAME, 'Button')
        username_box = inputs_location.find_element(By.CSS_SELECTOR, '[type="text"]')
        password_box = inputs_location.find_element(By.CSS_SELECTOR, '[type="password"]')

        logged_in = self.login(username_box, password_box, login_btn)

        if logged_in:
            # Wait for the schedule button to load, then click it
            self.driver.find_element(By.ID, 'buttons').find_element(By.CSS_SELECTOR, '[data-bind="click: ScheduleClicked"]').click()

            # Refactor with beautiful soup:
            # Wait condition for calendar:
            cal_wait_cond = EC.presence_of_element_located((By.CSS_SELECTOR, '[data-bind="foreach: ScheduleWeeks"]'))
            self.wait_to_find(cal_wait_cond)
            time.sleep(2)
            page_src = copy.deepcopy(self.driver.page_source)
            soup_current_month = BeautifulSoup(page_src, 'html.parser')
            # Check next month:
            self.driver.find_element(By.CSS_SELECTOR, '[data-bind="click: NextMonthClicked"]').click()
            self.wait_to_find(cal_wait_cond)
            time.sleep(2)
            next_month_page_src = copy.deepcopy(self.driver.page_source)
            soup_next_month = BeautifulSoup(next_month_page_src, 'html.parser')
            # Get the days scheduled for this and next month:
            scheduled_days_current_month = soup_current_month.find_all('div', class_="calendar-day scheduled")
            scheduled_days_next_month = soup_next_month.find_all('div', class_="calendar-day scheduled")
            schedule = [scheduled_days_current_month, scheduled_days_next_month]
            return self.parse_scheduled_days(schedule)
        else:
            logging.error(f"Unable to log in for user {self.user_in}, please retry with a higher timeout or check logic")

