from threading import Thread

from telegram import Update
from telegram.ext import TypeHandler, Updater

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

    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)

    def handle_update(_, update):
        # one thread per update: processing them sequentially caused concurrency problems
        Thread(target=bot.process_update, args=(update, )).start()

    # let the dispatcher be the only consumer of the update queue: it also
    # receives polling errors (e.g. TimedOut), already logged by the updater
    updater.dispatcher.add_handler(TypeHandler(Update, handle_update))
    updater.start_polling()
    updater.idle()


def create_workshits(month):
    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)
    active_users = [
        "GT",
        "CL",
        "AL",
        "CS",
        "AT",
        "SF",
        "SC",
        "PP",
        "RO",
        "SA",
    ]
    bot.create_workshits(month, active_users)


if __name__ == '__main__':
    # main()
    # create_workshits(7)
    main_loop()
    # pass
