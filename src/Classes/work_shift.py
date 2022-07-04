import datetime as dt
import time
from typing import Tuple


class WorkShift(object):
    def __init__(self, date: dt.date, start_time: dt.time, end_time = dt.time):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.shift_local_start_time, self.shift_local_end_time = self.initialize_local_dts()

    def initialize_local_dts(self) -> Tuple[dt.datetime, dt.datetime]:
        date_str = self.date.strftime('%Y%m%d')
        start_time_str = self.start_time.strftime("%I:%M %p")
        end_time_str = self.end_time.strftime("%I:%M %p")
        tz_str = self.generate_gmt_offset()
        start_dt_str = ' '.join([date_str, start_time_str, tz_str])
        end_dt_str = ' '.join([date_str, end_time_str, tz_str])
        start_localized_dt = dt.datetime.strptime(start_dt_str, '%Y%m%d %I:%M %p %z')
        end_localized_dt = dt.datetime.strptime(end_dt_str, '%Y%m%d %I:%M %p %z')
        return start_localized_dt, end_localized_dt

    @staticmethod
    def generate_gmt_offset() -> str:
        gmt_off_int = round(time.localtime().tm_gmtoff / 60 / 60 * 100)
        east_of_gmt = False
        if gmt_off_int < 0:
            east_of_gmt = True
            gmt_off_int *= -1
        gmt_off_string = str(gmt_off_int)
        if len(gmt_off_string) == 3:
            gmt_off_string = '0' + gmt_off_string
        if east_of_gmt:
            gmt_off_string = '-' + gmt_off_string
        return gmt_off_string
