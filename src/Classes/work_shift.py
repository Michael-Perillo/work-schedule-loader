import datetime as dt

class WorkShift(object):
    def __init__(self, date: dt.date, start_time: dt.time, end_time = dt.time):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time