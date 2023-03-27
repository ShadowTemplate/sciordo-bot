import time
from datetime import date, datetime

import telegram
from telegram.ext import Updater

from sciordo_bot.constants import BOT_COMMANDS, DROPBOX_UPDATES_DIR_PATH, WORKSHITS, \
    UK_USERS
from sciordo_bot.credentials import SCIORDO_BOT_TOKEN, SPREADSHIT_ID
from sciordo_bot.dropbox_service import DropboxService
from sciordo_bot.logger import get_application_logger
from sciordo_bot.sheet_service import SheetService
from sciordo_bot.time_utils import now_utc, pretty_str

log = get_application_logger()

class SciordoBot:

    def __init__(self, storage: DropboxService, sheet: SheetService):
        self._bot = telegram.Bot(token=SCIORDO_BOT_TOKEN)
        self._storage = storage
        self._sheet = sheet
        self.spreadshit = sheet.get_sheet(SPREADSHIT_ID)

    def update_inline_keyboard(self, user_id):
        kb = [
            [telegram.KeyboardButton(command)] for command in BOT_COMMANDS
        ]
        kb_markup = telegram.ReplyKeyboardMarkup(kb)
        message = "Aggiornata la lista di comandi! 🐦\n"
        for command, info in BOT_COMMANDS.items():
            message += f"\n\n{command}: {info[1]}"
        self._bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=kb_markup
        )

    def process_batch_updates(self):
        log.info(f"Processing updates...")
        for update in self._bot.get_updates():
            self.process_update(update)
        log.info(f"Processed updates.")

    def process_update(self, update):
        log.info(update)
        update_id = str(update['update_id'])
        update_file = f"{DROPBOX_UPDATES_DIR_PATH}/{update_id}.txt"
        log.debug(f"Checking if file {update_file} exists.")
        if self._storage.file_exists(update_file):
            log.info(f"Skipping already processed message...")
            return
        log.info(f"Processing new message...")
        if hasattr(update, 'message') and hasattr(update.message, 'text'):
            if update.message.text in BOT_COMMANDS:
                log.info(f"Processing command...")
                method_name = f"process_command_{BOT_COMMANDS[update.message.text][0]}"
                method = getattr(self, method_name)
                method(update)
                log.info(f"Processed command.")
        log.info(f"Processed new message.")
        log.info(f"Storing update_id...")
        self._storage.create_file(update_file)
        log.info(f"Stored update_id.")

    def get_current_workshit(self, update):
        sender_id = str(update['message']['chat']['id'])
        month = date.today().month
        workshit_id = f"{month}.{WORKSHITS[sender_id]}"
        log.debug(f"Workshit id: {workshit_id}")
        return self.spreadshit.worksheet(workshit_id)

    def _get_now_coord(self, update):
        now_ms = now_utc()
        log.info(pretty_str(now_ms))
        now_dt = datetime.fromtimestamp(now_ms / 1000.0)
        day = now_dt.day
        row = day + 1  # row offset
        hour = now_dt.hour
        hour += 1  # legal time
        user_id = str(update['message']['chat']['id'])
        # handle "next day" for CET users
        if user_id not in UK_USERS and hour == 23:
            hour = -1
            row += 1
        col = hour + 2  # col offset
        if user_id not in UK_USERS:
            col += 1  # UTC -> CET timezone
        return row, col

    def _get_cell_from_row_col(self, row, col):
        return f"{chr(ord('@') + col)}{row}"

    def _log_poo(self, update, workshit, row, col):
        cell = self._get_cell_from_row_col(row, col)
        log.info(f"Logging poo for {update['message']['chat']['id']} at {cell}...")
        value = workshit.get(cell)
        if not value:
            value = ''
        else:
            value = value[0][0]
        workshit.update_cell(row=row, col=col, value=value + '💩')
        log.info(f"Logged poo for {update['message']['chat']['id']} at {cell}.")
        self._bot.send_message(
            chat_id=update['message']['chat']['id'],
            text=f"Loggata una 💩 tra le {col - 2}.00 e le {col - 1}.00!"
                 f"\n\nÈ bello cagare! 🐦",
        )

    def process_command_new_poo(self, update):
        workshit = self.get_current_workshit(update)
        row, col = self._get_now_coord(update)
        self._log_poo(update, workshit, row, col)

    def process_command_new_poo_1_hr_ago(self, update):
        workshit = self.get_current_workshit(update)
        row, col = self._get_now_coord(update)
        col -= 1
        self._log_poo(update, workshit, row, col)

    def process_command_new_poo_2_hrs_ago(self, update):
        workshit = self.get_current_workshit(update)
        row, col = self._get_now_coord(update)
        col -= 2
        self._log_poo(update, workshit, row, col)

    def process_command_delete_last_poo(self, update):
        workshit = self.get_current_workshit(update)
        row, col = self._get_now_coord(update)
        while col > 0:
            cell = self._get_cell_from_row_col(row, col)
            value = workshit.get(cell)
            if not value:
                col -= 1
                continue

            value = value[0][0]
            log.info(f"Deleting poo for {update['message']['chat']['id']} at {cell}...")
            workshit.update_cell(row=row, col=col, value=value[:-1])
            log.info(f"Deleted poo for {update['message']['chat']['id']} at {cell}.")
            self._bot.send_message(
                chat_id=update['message']['chat']['id'],
                text=f"Cancellata una 💩 tra le {col - 2}.00 e le {col - 1}.00!"
                     f"\n\nCagare è una trasformazione irreversibile! 🐦",
            )
            break

    def process_command_recap_poo(self, update):
        workshit = self.get_current_workshit(update)
        row, col = self._get_now_coord(update)
        poos = []
        while col > 1:
            cell = self._get_cell_from_row_col(row, col)
            value = workshit.get(cell)
            if value:
                value = value[0][0]
                poos.append((col - 2, value))
            col -= 1
        poos.reverse()
        message = "La tua giornata di 💩:\n\n"
        message += "\n".join(
            [f"{hour}.00 - {hour + 1}.00: {value}" for hour, value in poos]
        )
        self._bot.send_message(
            chat_id=update['message']['chat']['id'],
            text=f"{message}"
                 f"\n\nNon è mai troppo tardi per cagare! 🐦",
        )

def main():
    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)
    for user in WORKSHITS:
        bot.update_inline_keyboard(user)
    # bot.process_batch_updates()


def main_loop():
    storage = DropboxService()
    sheet = SheetService()
    bot = SciordoBot(storage, sheet)
    updater = Updater(token=SCIORDO_BOT_TOKEN)
    queue = updater.start_polling()
    while True:
        try:
            update = queue.get()
            bot.process_update(update)
        except Exception as exc:
            log.error(exc)
            time.sleep(10)


if __name__ == '__main__':
    # main()
    main_loop()
