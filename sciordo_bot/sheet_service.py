from tempfile import NamedTemporaryFile
import gspread
from sciordo_bot.credentials import DRIVE_SECRETS_JSON, SPREADSHIT_ID

from oauth2client.service_account import ServiceAccountCredentials
from sciordo_bot.logger import get_application_logger

log = get_application_logger()


class SheetService:

    def __init__(self, drive_secrets_json=DRIVE_SECRETS_JSON):
        # emulate a json file with credentials
        with NamedTemporaryFile('w', delete=False) as json_f:
            json_f.write(drive_secrets_json)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            json_f.name,
            scopes,
        )
        self._service = gspread.authorize(credentials)

    @property
    def service(self):
        return self._service

    def get_sheet(self, sheet_id):
        return self._service.open_by_key(sheet_id)


def main():
    sheets = SheetService()
    spreadshit = sheets.get_sheet(SPREADSHIT_ID)
    print(spreadshit)


if __name__ == '__main__':
    main()
