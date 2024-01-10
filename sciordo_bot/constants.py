MAX_API_RETRY_ATTEMPTS = 15

SECRETS_UNTRACKED_FILE = "sciordo_bot.secrets.py"
DROPBOX_BOT_DIR_PATH = '/dev/sciordo-bot'
DROPBOX_UPDATES_DIR_PATH = f"{DROPBOX_BOT_DIR_PATH}/updates"

BOT_COMMANDS = {
    '💩 🎉': ("new_poo", "Logga una 💩 per quest'ora."),
    '💩 🕑 -1': ("new_poo_1_hr_ago", "Logga una 💩 per un'ora fa."),
    '💩 🕑 -2': ("new_poo_2_hrs_ago", "Logga una 💩 per due ore fa."),
    '💩 ❌': ("delete_last_poo", "Elimina l'ultima 💩 registrata oggi."),
    '💩 📊': ("recap_poo", "Recap delle 💩 di oggi."),
}

WORKSHITS = {
    '45845150': 'GT',
    '297848818': 'DS',
    '114759301': 'SL',
    '159727632': 'RM',
    '196433818': 'CL',
    '172437749': 'AL',
    '123503802': 'CT',
    '69030708': 'CS',
    '810252069': 'VS',
    '78818215': 'GC',
    '32309434': 'MU',
    '220383849': 'AA',
    '136030510': 'HZ',
    '593072857': 'DD',
    '101601579': 'AT',
    '771596583': 'ED',
    '276697560': 'RT',
    '255377477': 'SC',
    '691801776': 'SF',
    '193465787': 'FF',
    '41323058': 'LS',
    '5866235955': 'VG',
    '1557344909': 'PP',
    '189717759': 'SP',
    '172216099': 'MB',
}

UK_USERS = ['114759301', '159727632']
