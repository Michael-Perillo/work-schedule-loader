import sys
from src.config.Credential_Dir.CREDENTIALS import ARI_USER, JETS_USER, TAYL_USER, PASSWD
from src.config.Credential_Dir.CALENDAR_IDS import ARI_SCHEDULE_ID, JESS_SCHEDULE_ID, TAYLOR_SCHEDULE_ID
from src.Classes.Google_Calendar_Writer import LushGoogleCalendarWriter

USERS_DICT = {
    ARI_USER: ARI_SCHEDULE_ID,
    JETS_USER: JESS_SCHEDULE_ID,
    TAYL_USER: TAYLOR_SCHEDULE_ID
}


def main():
    for user, calendar in USERS_DICT.items():
        LushGoogleCalendarWriter(user, PASSWD, calendar)


if __name__ == '__main__':
    sys.exit(main())