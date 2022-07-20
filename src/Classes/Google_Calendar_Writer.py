from __future__ import print_function
import os.path
import datetime as dt
import logging
from typing import Optional, Dict, Tuple

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.Classes.work_shift import WorkShift
from src.Classes.Schedule_Loader import ScheduleLoader
from src.config.LOADER_CREDENTIALS_DIRECTORY import CRED_DIR, TOKEN_DIR


class LushGoogleCalendarWriter(object):

    def __init__(self, user_in: str, user_pass: str, calendar_id: str):
        self._SCOPES = ['https://www.googleapis.com/auth/calendar']
        self._creds = self.load_gcalendar_api_credentials()
        self._calendar_id = calendar_id
        if self._creds is not None:
            try:
                self.service = build('calendar', 'v3', credentials=self._creds)
                self.load_user_schedule(user_in, user_pass, self._calendar_id)
            except HttpError as error:
                print('An error occurred: %s' % error)
        else:
            logging.error("Credentials failed to initialize, raising error")
            raise ValueError(
                "Error generating credentials for google calendar api, check token and google api settings")

    @staticmethod
    def get_start_end_for_event(event: dict) -> Tuple[Optional[dt.datetime], Optional[dt.datetime]]:
        start_dict, end_dict = event.get('start'), event.get('end')
        start_dt, end_dt = None, None
        if start_dict is not None:
            _start_dt = start_dict.get('dateTime')
            if _start_dt is not None:
                start_dt = dt.datetime.fromisoformat(_start_dt)

        if end_dict is not None:
            _end_dt = end_dict.get('dateTime')
            if _end_dt is not None:
                end_dt = dt.datetime.fromisoformat(_end_dt)

        return start_dt, end_dt

    @staticmethod
    def create_event(start_dt: dt.datetime, end_dt: dt.datetime) -> dict:
        # See https://developers.google.com/calendar/api/v3/reference/events for fields
        event = {
            'summary': 'Lush Shift',
            'location': '1961 Chain Bridge Rd Unit G7U, McLean, VA 22102',
            'description': 'Workin hard for the money! Go baby!',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 90},
                    {'method': 'popup', 'minutes': 45},
                ],
            },
        }
        return event

    def load_gcalendar_api_credentials(self) -> Optional[dict]:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(TOKEN_DIR):
            creds = Credentials.from_authorized_user_file(TOKEN_DIR, self._SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except RefreshError:
                        print("Token expired, need to reauthenticate")
                        os.remove(TOKEN_DIR)

        if not os.path.exists(TOKEN_DIR):
            # If there are no (valid) credentials available, let the user log in.
            flow = InstalledAppFlow.from_client_secrets_file(CRED_DIR, self._SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(TOKEN_DIR, 'w') as token:
                token.write(creds.to_json())
        return creds

    def update_schedule(self, up_to_date: Dict[str, WorkShift]):
        # Call the Calendar API, 'Z' indicates UTC time
        now = dt.datetime.fromisoformat(dt.datetime.utcnow().date().isoformat()).isoformat() + 'Z'
        events_result = self.service.events().list(calendarId=self._calendar_id, timeMin=now,
                                                   maxResults=30, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
            return

        for event in events:
            event_name = event.get('summary')
            if event_name != 'Lush Shift':
                continue

            start_dt, end_dt = self.get_start_end_for_event(event)
            if start_dt is not None:
                start_date_string = start_dt.strftime('%Y%m%d')
                possibly_updated_shift = up_to_date.get(start_date_string)
                if possibly_updated_shift is not None and end_dt is not None:
                    print(f"Found shift for user on date {start_date_string}, comparing:")
                    if possibly_updated_shift.shift_local_start_time != start_dt or possibly_updated_shift.shift_local_end_time != end_dt:
                        print('Deleting event from calendar and replacing, dates do not match')
                        kwargs = {'calendarId': self._calendar_id,
                                  'eventId': event.get('id'),
                                  'sendNotifications': False}
                        rq = self.service.events().delete(**kwargs)
                        resp = rq.execute()
                    else:
                        print('Up to date, deleting from dictionary')
                        del up_to_date[start_date_string]
        return

    def load_user_schedule(self, user_in: str, user_pass: str, calendar_id: str):
        # Get the up to date schedule from website
        schedule_dict = ScheduleLoader(user_in, user_pass, 20).schedule_dict
        # Delete events in the calendar that have updated start and end times, or delete entries
        # that are not updated in schedule dict:
        self.update_schedule(up_to_date=schedule_dict)
        # Add the remaining shifts to the calendar:
        for _, work_shift_obj in schedule_dict.items():
            new_event_body = self.create_event(work_shift_obj.shift_local_start_time,
                                               work_shift_obj.shift_local_end_time)
            new_event = self.service.events().insert(calendarId=calendar_id, body=new_event_body).execute()
            print('Event created: %s' % (new_event.get('htmlLink')))
