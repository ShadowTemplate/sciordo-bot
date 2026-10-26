import calendar
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo

import telegram
from gspread.exceptions import WorksheetNotFound

from sciordo_bot.constants import ADMIN_CHAT_ID, BOT_COMMANDS, DROPBOX_UPDATES_DIR_PATH, \
    NEXT_MONTH_WORKSHITS_DAY, WORKSHIT_TEMPLATE, WORKSHITS, TIMEZONE
from sciordo_bot.credentials import SCIORDO_BOT_TOKEN, SPREADSHIT_IDS
from sciordo_bot.dropbox_service import DropboxService
from sciordo_bot.logger import get_application_logger
from sciordo_bot.sheet_service import SheetService
from sciordo_bot.time_utils import DEFAULT_DATE_FORMAT

log = get_application_logger()

class SciordoBot:

    def __init__(self, storage: DropboxService, sheet: SheetService):
        self._bot = telegram.Bot(token=SCIORDO_BOT_TOKEN)
        self._storage = storage
        self._sheet = sheet
        self._spreadshits = {}  # by year
        # updates are processed in parallel: don't create the same workshit twice
        self._workshit_creation_lock = Lock()

    def update_inline_keyboard(self, chat_id):
        kb = [
            [telegram.KeyboardButton(command)] for command in BOT_COMMANDS
        ]
        kb_markup = telegram.ReplyKeyboardMarkup(kb)
        message = "Aggiornata la lista di comandi! 🐦\n"
        for command, info in BOT_COMMANDS.items():
            message += f"\n\n{command}: {info[1]}"
        self._bot.send_message(
            chat_id=chat_id,
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
        if not hasattr(update, 'message'):
            self._bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Update from unknown user: {update}.",
            )
        elif hasattr(update.message, 'from_user') and str(update.message.from_user.id) not in WORKSHITS.keys():
            self._bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Update from unknown user: {update.message}.",
            )
        elif hasattr(update.message, 'text'):
            if update.message.text in BOT_COMMANDS:
                log.info(f"Processing command...")
                method_name = f"process_command_{BOT_COMMANDS[update.message.text][0]}"
                method = getattr(self, method_name)
                try:
                    method(update)
                except Exception:
                    log.exception(f"Failed to process command {method_name}.")
                    self._bot.send_message(
                        chat_id=update.message.chat_id,
                        text="Qualcosa è andato storto, riprova più tardi! 🐦",
                    )
                    return
                log.info(f"Processed command.")
        log.info(f"Processed new message.")
        log.info(f"Storing update_id...")
        self._storage.create_file(update_file)
        log.info(f"Stored update_id.")

    def _now_local(self, hours_ago=0):
        # subtract in UTC so the result stays correct across DST changes
        now_dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        return now_dt.astimezone(ZoneInfo(TIMEZONE))

    def get_current_workshit(self, chat_id):
        return self._get_workshit(chat_id, self._now_local())

    def _get_spreadshit(self, year):
        if year not in self._spreadshits:
            if year not in SPREADSHIT_IDS:
                raise KeyError(f"No spreadshit configured for {year}.")
            self._spreadshits[year] = self._sheet.get_sheet(SPREADSHIT_IDS[year])
        return self._spreadshits[year]

    def _get_workshit(self, chat_id, dt):
        user = WORKSHITS[chat_id]
        workshit_id = f"{dt.month}.{user}"
        log.debug(f"Workshit id: {workshit_id}")
        try:
            return self._get_spreadshit(dt.year).worksheet(workshit_id)
        except WorksheetNotFound:
            # first poo of the month of a user dropped for inactivity
            return self._create_workshit(dt.year, dt.month, user)

    def _create_workshit(self, year, month, user):
        spreadshit = self._get_spreadshit(year)
        workshit_id = f"{month}.{user}"
        with self._workshit_creation_lock:
            try:  # another thread may have created it in the meantime
                return spreadshit.worksheet(workshit_id)
            except WorksheetNotFound:
                pass
            log.info(f"Creating new workshit {workshit_id}...")
            template = self._get_workshit_template(year)
            workshit = template.duplicate(
                insert_sheet_index=0,
                new_sheet_name=workshit_id,
            )
            # the dates in column A are computed from the month name in A1
            workshit.update_acell('A1', calendar.month_name[month])
            log.info(f"Created new workshit {workshit_id}.")
            return workshit

    def _get_workshit_template(self, year):
        spreadshit = self._get_spreadshit(year)
        try:
            return spreadshit.worksheet(WORKSHIT_TEMPLATE)
        except WorksheetNotFound:
            pass
        # a new year's spreadshit starts empty: copy the previous year's template
        log.info(f"Copying the workshit template to the {year} spreadshit...")
        previous_template = self._get_spreadshit(year - 1).worksheet(WORKSHIT_TEMPLATE)
        copied = previous_template.copy_to(spreadshit.id)
        template = spreadshit.get_worksheet_by_id(copied['sheetId'])
        template.update_title(WORKSHIT_TEMPLATE)
        # the dates in column A are computed from the year in A33
        template.update_acell('A33', year)
        log.info(f"Copied the workshit template to the {year} spreadshit.")
        return template

    def _get_now_coord(self, chat_id):
        return self._get_coord(self._now_local())

    def _get_coord(self, dt):
        log.info(dt.strftime(DEFAULT_DATE_FORMAT))
        row = dt.day + 1  # row offset
        col = dt.hour + 2  # col offset
        return row, col

    def _get_cell_from_row_col(self, row, col):
        return f"{chr(ord('@') + col)}{row}"

    def _log_poo(self, chat_id, workshit, row, col):
        cell = self._get_cell_from_row_col(row, col)
        log.info(f"Logging poo for {chat_id} at {cell}...")
        value = workshit.get(cell)
        if not value:
            value = ''
        else:
            value = value[0][0]
        workshit.update_cell(row=row, col=col, value=value + '💩')
        log.info(f"Logged poo for {chat_id} at {cell}.")
        self._bot.send_message(
            chat_id=chat_id,
            text=f"Loggata una 💩 tra le {col - 2}.00 e le {col - 1}.00!"
                 f"\n\nÈ bello cagare! 🐦",
        )

    def _log_poo_hours_ago(self, update, hours_ago):
        chat_id = str(update['message']['chat']['id'])
        poo_dt = self._now_local(hours_ago)
        # the poo may belong to the previous day or month
        workshit = self._get_workshit(chat_id, poo_dt)
        row, col = self._get_coord(poo_dt)
        self._log_poo(chat_id, workshit, row, col)

    def process_command_new_poo(self, update):
        self._log_poo_hours_ago(update, 0)

    def process_command_new_poo_1_hr_ago(self, update):
        self._log_poo_hours_ago(update, 1)

    def process_command_new_poo_2_hrs_ago(self, update):
        self._log_poo_hours_ago(update, 2)

    def process_command_delete_last_poo(self, update):
        chat_id = str(update['message']['chat']['id'])
        workshit = self.get_current_workshit(chat_id)
        row, col = self._get_now_coord(chat_id)
        while col > 1:  # column A holds the date
            cell = self._get_cell_from_row_col(row, col)
            value = workshit.get(cell)
            if not value:
                col -= 1
                continue

            value = value[0][0]
            log.info(f"Deleting poo for {update['message']['chat']['id']} at {cell}...")
            workshit.update_cell(row=row, col=col, value=value[:-1])
            log.info(f"Deleted poo for {chat_id} at {cell}.")
            self._bot.send_message(
                chat_id=chat_id,
                text=f"Cancellata una 💩 tra le {col - 2}.00 e le {col - 1}.00!"
                     f"\n\nCagare è una trasformazione irreversibile! 🐦",
            )
            break
        else:
            self._bot.send_message(
                chat_id=chat_id,
                text="Nessuna 💩 da cancellare oggi! 🐦",
            )

    def process_command_recap_poo(self, update):
        chat_id = str(update['message']['chat']['id'])
        workshit = self.get_current_workshit(chat_id)
        row, col = self._get_now_coord(chat_id)
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
            chat_id=chat_id,
            text=f"{message}"
                 f"\n\nNon è mai troppo tardi per cagare! 🐦"
                 f"\n\nWorkshit: {workshit.url}",
        )

    def create_next_month_workshits(self, _bot=None, _job=None):
        # runs daily as a job: retrying on the following days is harmless,
        # because existing workshits are skipped
        now_dt = self._now_local()
        if now_dt.day < NEXT_MONTH_WORKSHITS_DAY:
            return
        try:
            created, dropped = self._create_next_month_workshits(now_dt)
        except Exception:
            log.exception("Failed to create next month's workshits.")
            self._bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="Failed to create next month's workshits, check the logs.",
            )
            return
        if created:
            self._bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Created next month's workshits for: {', '.join(created)}."
                     f"\n\nDropped for inactivity: {', '.join(dropped) or 'none'}.",
            )

    def _create_next_month_workshits(self, now_dt):
        next_dt = (now_dt.replace(day=1) + timedelta(days=32)).replace(day=1)
        spreadshit = self._get_spreadshit(now_dt.year)
        workshit_ids = {ws.title for ws in spreadshit.worksheets()}
        users = [u for u in WORKSHITS.values() if f"{now_dt.month}.{u}" in workshit_ids]
        if not users:
            return [], []
        # Z33 holds the month's total of poos
        response = spreadshit.values_batch_get([f"'{now_dt.month}.{u}'!Z33" for u in users])
        poos = [int(r.get('values', [['0']])[0][0] or 0) for r in response['valueRanges']]
        active = [u for u, p in zip(users, poos) if p > 0]
        dropped = [u for u, p in zip(users, poos) if p == 0]

        next_workshit_ids = {ws.title for ws in self._get_spreadshit(next_dt.year).worksheets()}
        created = [u for u in active if f"{next_dt.month}.{u}" not in next_workshit_ids]
        # each workshit is inserted first: create them in reverse to keep the users' order
        for user in reversed(created):
            self._create_workshit(next_dt.year, next_dt.month, user)
        return created, dropped
