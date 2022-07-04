from __future__ import print_function
import sys
import os.path
import datetime as dt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.config.LOADER_CREDENTIALS_DIRECTORY import CRED_DIR, TOKEN_DIR
from src.config.CREDENTIALS import ARI_USER, ARI_PASS
from src.config.CALENDAR_IDS import ARI_SCHEDULE_ID
from src.Scripts.schedule_getter_storeforce import get_schedule_dict_for_user

# See https://developers.google.com/workspace/guides/create-credentials#desktop-app for how to generate credentials
# See https://developers.google.com/calendar/api/quickstart/python for more information, can add token to remove auth
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


def main():
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

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = dt.datetime.fromisoformat(dt.datetime.utcnow().date().isoformat()).isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId=ARI_SCHEDULE_ID, timeMin=now,
                                              maxResults=30, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')

        # Delete events from schedule dict that are already found in the calendar:
        schedule_dict = get_schedule_dict_for_user(ARI_USER, ARI_PASS)
        for event in events:
            start_dict = event.get('start')
            if start_dict is not None:
                _start_dt = start_dict.get('dateTime')
                if _start_dt is not None:
                    start_dt = dt.datetime.fromisoformat(_start_dt)
                    start_date_string = start_dt.strftime('%Y%m%d')
                    if schedule_dict.get(start_date_string) is not None:
                        print(f"Found shift for date {start_date_string}, skipping")
                        del schedule_dict[start_date_string]

        # Add the remaining shifts to the calendar:
        for _, work_shift_obj in schedule_dict.items():
            new_event_body = create_event(work_shift_obj.shift_local_start_time, work_shift_obj.shift_local_end_time)
            new_event = service.events().insert(calendarId=ARI_SCHEDULE_ID, body=new_event_body).execute()
            print('Event created: %s' % (new_event.get('htmlLink')))

    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    sys.exit(main())
