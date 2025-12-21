import calendar
import json
import sys
from collections import defaultdict
from datetime import datetime

from sciordo_bot.constants import WORKSHITS
from sciordo_bot.logger import get_application_logger
from sciordo_bot.secrets import TELEGRAM_NAMES_TO_SIGLA
from xlsx2csv import Xlsx2csv

log = get_application_logger()

WORK_DIR = "/home/gianvito/Downloads"

USERS = list(WORKSHITS.values())
MONTHS = list(range(1, 13))
HOURS = list(range(24))
DAYS = list(range(1, 32))


class Wrapped:
    def __init__(self, spreadshit_file, chat_history_file):
        self.spreadshit_file = spreadshit_file
        self.chat_history_file = chat_history_file
        self.workshit_by_users = defaultdict(lambda: defaultdict(list))
        self.active_workshit_by_users = defaultdict(lambda: defaultdict(list))
        self.poos_by_users = defaultdict(lambda: defaultdict(int))
        self.active_poos_by_users = defaultdict(lambda: defaultdict(int))
        self.csv_dir = f"{WORK_DIR}/spreadshit2023"

    def print(self):
        self.convert_to_csv()
        for user in USERS:
            for month in MONTHS:
                workshit_name = f"{month}.{user}"
                try:
                    workshit = self.get_workshit(workshit_name)
                    self.workshit_by_users[user][month] = workshit
                    if self.is_active_workshit(workshit):
                        self.active_workshit_by_users[user][month] = workshit
                except FileNotFoundError:
                    log.debug(f"Workshit not found: {workshit_name}")
        print(f"Users: {len(WORKSHITS)}")
        print()
        new_users = set()
        for month in MONTHS:
            monthly_users = set()
            for user in USERS:
                if month in self.workshit_by_users[user] and user not in new_users:
                    monthly_users.add(user)
                    new_users.add(user)
            if len(monthly_users) > 0:
                print(f"Users joining in {calendar.month_name[month]}: {list(monthly_users)}")
        print()
        inactive_users = list(set(USERS) - set(self.active_workshit_by_users.keys()))
        print(f"Inactive users: {len(inactive_users)} ({inactive_users})")
        print()
        active_december_users = [u for u in USERS if 12 in self.active_workshit_by_users[u]]
        print(f"Active users in December: {len(active_december_users)} ({active_december_users})")
        for user in inactive_users:
            USERS.remove(user)
        tot_workshits = 0
        for user, months in self.workshit_by_users.items():
            tot_workshits += len(months)
        print(f"Total number of workshits: {tot_workshits}")
        print()
        tot_poos = 0
        tot_poos_by_user = {}
        for user in USERS:
            user_poos = self._print_user_stats(user, active=False)
            tot_poos += user_poos
            tot_poos_by_user[user] = user_poos
            if len(self.active_workshit_by_users[user]) != len(self.workshit_by_users[user]):
                self._print_user_stats(user, active=True)
            else:
                print("Always active! :)")
            print()
        print(f"Total number of poos: {tot_poos}")
        self._print_aggregate_stats()
        print()
        messages_by_user = self._print_chat_stats()
        ratio_poos_messages = {
            user: tot_poos_by_user[user] / messages_by_user[TELEGRAM_NAMES_TO_SIGLA[user]]
            for user in USERS
        }
        print()
        print("Ratio poos/messages:")
        for user in sorted(ratio_poos_messages, key=ratio_poos_messages.get,
                           reverse=True):
            print(f"{user}: {ratio_poos_messages[user]} ratio {tot_poos_by_user[user]} poos / {messages_by_user[TELEGRAM_NAMES_TO_SIGLA[user]]} messages")

    def convert_to_csv(self):
        Xlsx2csv(
            self.spreadshit_file,
            outputencoding="utf-8"
        ).convert(
            self.csv_dir,
            sheetid=0,  # all workshits
        )

    def get_workshit(self, title):
        return open(f"{self.csv_dir}/{title}.csv", "r").readlines()

    def get_poo_number(self, workshit):
        return int(workshit[-1].strip("\n").split(',')[-1])

    def get_golden_poo_number(self, workshit):
        tot_golden = 0
        for day in workshit[1:-1]:
            day_hour = day.split(',')
            if '-' not in day_hour[0]:
                continue
            day = int(day_hour[0].split('-')[1])
            hours = day_hour[1:-1]
            for i in HOURS:
                if hours[i] != '' and i == day:
                    day_golden = hours[i].count('💩')
                    tot_golden += day_golden
                    if day_golden > 1:
                        print(f"Multiple golden poos in {workshit}!")  # didn't happen in 2023
        return tot_golden

    def _print_user_stats(self, user, active=True):
        if active:
            months = self.active_workshit_by_users[user]
        else:
            months = self.workshit_by_users[user]
        max_poos, max_month = 0, 0
        min_poos, min_month = sys.maxsize, 0
        for month in months:
            poos = self.get_poo_number(months[month])
            if active:
                self.active_poos_by_users[user][month] = poos
            else:
                self.poos_by_users[user][month] = poos
            if poos > max_poos:
                max_poos = poos
                max_month = month
            if min_poos >= poos > 0:
                min_poos = poos
                min_month = month
        if active:
            total_poos_user = sum(self.active_poos_by_users[user].values())
            total_months_user = len(self.active_workshit_by_users[user])
        else:
            total_poos_user = sum(self.poos_by_users[user].values())
            total_months_user = len(self.workshit_by_users[user])
        avg_poos_user = round(total_poos_user / total_months_user)
        label = "active" if active else "total"
        print(
            f"User: {user}, total poos: {total_poos_user}, monthly avg: {avg_poos_user} (over {total_months_user} {label} months)")
        if not active:
            print(f"Max month: {calendar.month_name[max_month]}, max poos: {max_poos}")
        print(f"Min month: {calendar.month_name[min_month]}, min poos: {min_poos}")
        if not active:
            golden_poos = 0
            max_golden_poos_month = None
            max_golden_poos_tot = 0
            for month_num, month_poos in self.workshit_by_users[user].items():
                monthly_golden = self.get_golden_poo_number(month_poos)
                if monthly_golden > max_golden_poos_tot:
                    max_golden_poos_month = month_num
                    max_golden_poos_tot = monthly_golden
                golden_poos += monthly_golden
            print(f"Total golden poos: {golden_poos}")
            if max_golden_poos_tot > 0:
                print(f"Golden month: {calendar.month_name[max_golden_poos_month]} ({max_golden_poos_tot} golden poos)")
        return total_poos_user

    def is_active_workshit(self, workshit):
        poos = self.get_poo_number(workshit)
        if poos < 4:
            return False
        in_a_row = 0
        for day in workshit[1:]:
            values = day.rstrip("\n").split(",")
            poo = int(values[-1])
            if poo > 0:
                in_a_row = 0
            else:
                in_a_row += 1
            if in_a_row >= 8:
                return False
        return True

    def _print_aggregate_stats(self):
        absolute_max_user, absolute_max_poos, absolute_max_month = None, 0, 0
        for user, months in self.workshit_by_users.items():
            for month in months:
                poos = self.get_poo_number(months[month])
                self.poos_by_users[user][month] = poos
                if poos > absolute_max_poos:
                    absolute_max_poos = poos
                    absolute_max_month = month
                    absolute_max_user = user
        print(f"{absolute_max_user}, absolute max month: {calendar.month_name[absolute_max_month]}, absolute max poos: {absolute_max_poos}")
        print()
        self._get_most_poos()

    def _get_most_poos(self):
        poos_by_month_day_hour_number = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        poos_by_month_day_number = defaultdict(lambda: defaultdict(int))
        poos_by_month_day_hour_people = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        poos_by_month_day_people = defaultdict(lambda: defaultdict(list))
        poos_by_hour_number = defaultdict(int)

        for month in MONTHS:
            for user in USERS:
                days_poos = self.workshit_by_users[user][month][1:-1]
                for day_num, day in enumerate(days_poos, start=1):
                    for hour in HOURS:
                        count = day.split(',')[hour+1].count('💩')
                        poos_by_month_day_hour_number[month][day_num][hour] += count
                        poos_by_month_day_number[month][day_num] += count
                        poos_by_hour_number[hour] += count
                        if hour == 4 and count > 0:
                            print(f"Nightly poos (between {hour}:00 and {hour+1}:00): {user} ({day_num} {calendar.month_name[month]})")
                        if count > 0:
                            poos_by_month_day_hour_people[month][day_num][hour].append(user)
                            poos_by_month_day_people[month][day_num].append(user)
        max_poos_hour = -1
        max_poos_day = -1
        max_poos_month = -1
        max_poos_number = 0
        for month in MONTHS:
            for day in DAYS:
                for hour in HOURS:
                    if poos_by_month_day_hour_number[month][day][hour] > max_poos_number:
                        max_poos_hour = hour
                        max_poos_day = day
                        max_poos_month = month
                        max_poos_number = poos_by_month_day_hour_number[month][day][hour]
        print(f"Max poos on {max_poos_day} {calendar.month_name[max_poos_month]} between {max_poos_hour} and {int(max_poos_hour) + 1} by {poos_by_month_day_hour_people[max_poos_month][max_poos_day][max_poos_hour]}: {max_poos_number}")
        max_poos_day = -1
        max_poos_month = -1
        max_poos_number = 0
        for month in MONTHS:
            for day in DAYS:
                if poos_by_month_day_number[month][day] > max_poos_number:
                    max_poos_day = day
                    max_poos_month = month
                    max_poos_number = poos_by_month_day_number[month][day]
        print(f"Max poos on {max_poos_day} {calendar.month_name[max_poos_month]} by {list(set(poos_by_month_day_people[max_poos_month][max_poos_day]))}: {max_poos_number}")
        print()
        print(f"Total poos by hour (over all users/workshits):")
        for hour in HOURS:
            print(f"{hour}:00 - {hour + 1}:00 with {poos_by_hour_number[hour]} poos")
        peak_hour = min(poos_by_hour_number, key=poos_by_hour_number.get)
        print(f"Min peak hour: {peak_hour}:00 - {peak_hour + 1}:00")
        peak_hour = max(poos_by_hour_number, key=poos_by_hour_number.get)
        print(f"Max peak hour: {peak_hour}:00 - {peak_hour + 1}:00")
        print()
        print(f"Users pooing last minute of 2023:")
        for user in USERS:
            for hour in range(-2, -12, -1):
                dec_31_poos = self.workshit_by_users[user][12][31]
                if dec_31_poos.split(',')[hour] != '':
                    print(f"{user} between {25 + hour} and {25 + hour + 1}")

    def _print_chat_stats(self):
        with open(self.chat_history_file) as json_f:
            history = json.load(json_f)
        messages = history['messages']
        print(f"Total number of messages in Caccamici 💩: {len(messages)}")
        tot_poo_emoji = 0
        tot_messages_by_user = defaultdict(int)
        tot_messages_by_day = defaultdict(int)
        for message in messages:
            text = message['text']
            tot_poo_emoji += text.count('💩')
            if 'from' in message:
                user = message['from']
                tot_messages_by_user[user] += 1
            date_time = datetime.fromtimestamp(int(message['date_unixtime']))
            day = str(date_time).split(' ')[0]
            tot_messages_by_day[day] +=1
        print(f"Emoji 💩 used {tot_poo_emoji} times")
        print()
        print(f"Tot messages by users:")
        for user in sorted(tot_messages_by_user, key=tot_messages_by_user.get, reverse=True):
            print(f"{user}: {tot_messages_by_user[user]} messages")
        print()
        most_active_day = max(tot_messages_by_day, key=tot_messages_by_day.get)
        print(f"Most active day: {most_active_day} (yyyy-dd-mm) with {tot_messages_by_day[most_active_day]} messages")
        return tot_messages_by_user


def main():
    spreadshit_file = f"{WORK_DIR}/Spreadshit 2023.xlsx"
    chat_history_file = f"{WORK_DIR}/caccaamici_chat.json"
    Wrapped(spreadshit_file, chat_history_file).print()


if __name__ == '__main__':
    main()
