import json
import os
from importlib import import_module

from sciordo_bot.constants import SECRETS_UNTRACKED_FILE


def _get_credential_from_secrets(credential_key):
    try:  # will succeed locally if secret.py file is available
        secret_module = import_module(SECRETS_UNTRACKED_FILE.rstrip(".py"))
        # print(getattr(secret_module, 'USERS'))
        return getattr(secret_module, credential_key)
    except ModuleNotFoundError:
        return None


def get_credential(credential_key):
    return os.environ.get(credential_key, _get_credential_from_secrets(credential_key))


DRIVE_SECRETS_JSON = get_credential('DRIVE_SECRETS_JSON')
DROPBOX_REFRESH_TOKEN = get_credential('DROPBOX_REFRESH_TOKEN')
DROPBOX_APP_KEY = get_credential('DROPBOX_APP_KEY')
DROPBOX_APP_SECRET = get_credential('DROPBOX_APP_SECRET')

def _parse_spreadshit_ids(spreadshit_ids):
    # {year: spreadshit_id}: a dict in the secrets file, a JSON string in the environment
    if isinstance(spreadshit_ids, str):
        spreadshit_ids = json.loads(spreadshit_ids)
    return {int(year): spreadshit_id for year, spreadshit_id in (spreadshit_ids or {}).items()}


SPREADSHIT_IDS = _parse_spreadshit_ids(get_credential('SPREADSHIT_IDS'))
SCIORDO_BOT_TOKEN = get_credential('SCIORDO_BOT_TOKEN')
