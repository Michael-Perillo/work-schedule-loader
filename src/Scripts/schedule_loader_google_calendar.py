from __future__ import print_function
import sys
import os.path
import datetime as dt
from typing import Optional, Dict, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.Classes.work_shift import WorkShift
from src.config.LOADER_CREDENTIALS_DIRECTORY import CRED_DIR, TOKEN_DIR
from src.config.CREDENTIALS import ARI_USER, JETS_USER, ARI_PASS
from src.config.CALENDAR_IDS import ARI_SCHEDULE_ID, JESS_SCHEDULE_ID
from src.Scripts.schedule_getter_storeforce import get_schedule_dict_for_user

# See https://developers.google.com/workspace/guides/create-credentials#desktop-app for how to generate credentials
# Based on https://developers.google.com/calendar/api/quickstart/python, see for more info, can remove token to make more secure
# See https://developers.google.com/calendar/api/guides/auth for scopes

SCOPES = ['https://www.googleapis.com/auth/calendar']


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


def load_gcalendar_api_credentials() -> Optional[dict]:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_DIR):
        creds = Credentials.from_authorized_user_file(TOKEN_DIR, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CRED_DIR, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_DIR, 'w') as token:
            token.write(creds.to_json())
    return creds


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


def update_schedule(service: build, calendar_id: str, up_to_date: Dict[str, WorkShift]):
    # Call the Calendar API, 'Z' indicates UTC time
    now = dt.datetime.fromisoformat(dt.datetime.utcnow().date().isoformat()).isoformat() + 'Z'
    events_result = service.events().list(calendarId=calendar_id, timeMin=now,
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

        start_dt, end_dt = get_start_end_for_event(event)
        if start_dt is not None:
            start_date_string = start_dt.strftime('%Y%m%d')
            possibly_updated_shift = up_to_date.get(start_date_string)
            if possibly_updated_shift is not None and end_dt is not None:
                print(f"Found shift for user on date {start_date_string}, comparing:")
                if possibly_updated_shift.shift_local_start_time != start_dt or possibly_updated_shift.shift_local_end_time != end_dt:
                    print('Deleting event from calendar and replacing, dates do not match')
                    service.events().delete(calendar_id=calendar_id, eventId=event.get('id')).execute()
                else:
                    print('Up to date, deleting from dictionary')
                    del up_to_date[start_date_string]
    return


def load_user_schedule(user_in: str, user_pass: str, calendar_id: str):
    creds = load_gcalendar_api_credentials()
    if creds is not None:
        try:
            service = build('calendar', 'v3', credentials=creds)
            # Get the up to date schedule from website
            schedule_dict = get_schedule_dict_for_user(user_in, user_pass)
            # Delete events in the calendar that have updated start and end times, or delete entries
            # that are not updated in schedule dict:
            update_schedule(service, calendar_id, schedule_dict)

            # Add the remaining shifts to the calendar:
            for _, work_shift_obj in schedule_dict.items():
                new_event_body = create_event(work_shift_obj.shift_local_start_time,
                                              work_shift_obj.shift_local_end_time)
                new_event = service.events().insert(calendarId=calendar_id, body=new_event_body).execute()
                print('Event created: %s' % (new_event.get('htmlLink')))

        except HttpError as error:
            print('An error occurred: %s' % error)
    else:
        raise ValueError("Error generating credentials for google calendar api, check token and google api settings")
    return


def main():
    load_user_schedule(ARI_USER, ARI_PASS, ARI_SCHEDULE_ID)
    load_user_schedule(JETS_USER, ARI_PASS, JESS_SCHEDULE_ID)


if __name__ == '__main__':
    sys.exit(main())
