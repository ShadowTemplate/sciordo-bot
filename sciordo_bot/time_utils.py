import time

from datetime import datetime

DEFAULT_DATE_FORMAT = "%d-%m-%Y, %H:%M:%S"

def now() -> int:
    return int(round(time.time() * 1000))


def now_utc() -> int:
    # please note this function does not always return the same value of now(),
    # because the local timezone (used by now()) can be different (e.g. 'CET').
    return datetime_to_ms(datetime.utcnow())


def datetime_to_ms(dt):
    return int(dt.timestamp() * 1000)

def pretty_str(now_ms: int, date_format=DEFAULT_DATE_FORMAT) -> str:
    now_dt = datetime.fromtimestamp(now_ms / 1000.0)
    return now_dt.strftime(date_format)

def get_local_timezone():
    return str(datetime.now().astimezone().tzinfo)
