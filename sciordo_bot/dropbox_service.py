import dropbox
from dropbox import Dropbox
from dropbox.exceptions import ApiError

from sciordo_bot.constants import DROPBOX_BOT_DIR_PATH
from sciordo_bot.credentials import DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, DROPBOX_APP_SECRET
from sciordo_bot.logger import get_application_logger

log = get_application_logger()


class DropboxService:

    def __init__(self):
        self._service = Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
        )

    @property
    def service(self):
        return self._service

    def list_files(self, path, cursor=None):
        if not cursor:
            results = self._service.files_list_folder(path)
        else:
            results = self._service.files_list_folder_continue(cursor)
        items = results.entries
        if not results.has_more:
            return items
        return items + self.list_files(path, results.cursor)

    def file_exists(self, file_id):
        try:
            self._service.files_get_metadata(file_id)
            return True
        except ApiError as exc:
            if isinstance(exc.error, dropbox.files.GetMetadataError):
                return False
            raise exc

    def create_file(self, name):
        log.info(f"Storing file {name}...")
        results = self._service.files_upload(bytes(), name, mute=True)
        log.info(f"Stored file {name}: {results}")


def main():
    storage_service = DropboxService()
    print(storage_service.list_files(DROPBOX_BOT_DIR_PATH))


if __name__ == '__main__':
    main()
