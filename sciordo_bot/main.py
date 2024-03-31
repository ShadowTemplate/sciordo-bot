import time
from threading import Thread

from telegram.ext import Updater

from sciordo_bot.bot import SciordoBot
from sciordo_bot.constants import WORKSHITS
from sciordo_bot.credentials import SCIORDO_BOT_TOKEN
from sciordo_bot.dropbox_service import DropboxService
from sciordo_bot.logger import get_application_logger
from sciordo_bot.sheet_service import SheetService

log = get_application_logger()


def main():
    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)
    for user in WORKSHITS:
        if user in []:
            bot.update_inline_keyboard(user)

    # fake_update = {'message': {'chat': {'id': 45845150}}}
    # bot.process_command_new_poo(fake_update)
    # bot.process_command_recap_poo(fake_update)
    # bot.process_command_new_poo_2_hrs_ago(fake_update)
    # bot.process_batch_updates()


def main_loop():
    updater = Updater(token=SCIORDO_BOT_TOKEN)
    queue = updater.start_polling()

    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)

    def process_update_fn(new_update):
        bot.process_update(new_update)

    while True:
        try:
            update = queue.get()
            thread = Thread(target=process_update_fn, args=(update, ))
            thread.start()
            # thread.join()  # cause concurrency problems
        except Exception as exc:
            log.error(exc)
            time.sleep(10)


def create_workshits(month):
    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)
    active_users = [
        "GT",
        "DS",
        "CL",
        "AL",
        "CS",
        "AT",
        "SF",
        "FF",
        "VS",
        "RT",
        "SC",
        "SP",
        "PP",
        "MB",
        "ED",
        "VL",
        "FV",
    ]
    bot.create_workshits(month, active_users)


if __name__ == '__main__':
    # main()
    # create_workshits(4)
    main_loop()
