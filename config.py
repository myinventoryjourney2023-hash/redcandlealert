# ==========================
# MARKET SETTINGS
# ==========================

MARKET = "NSE"
SCAN_MODE = "FO"          # FO, NIFTY500, SECTOR, WATCHLIST

# ==========================
# SCANNER SETTINGS
# ==========================

TOP_GAINERS = 10
TOP_LOSERS = 10

TIMEFRAME = "5m"
PERIOD = "1d"

REFRESH_SECONDS = 300

# ==========================
# PERFORMANCE
# ==========================

MAX_THREADS = 20
RETRY_COUNT = 2
REQUEST_TIMEOUT = 15

# ==========================
# STRATEGY
# ==========================

ACTIVE_STRATEGY = "LOW_VOLUME"

LONG_ENABLED = True
SHORT_ENABLED = True

# ==========================
# TELEGRAM
# ==========================

USE_TELEGRAM = False

# ==========================
# WATCHLIST
# ==========================

WATCHLIST = [
    "RELIANCE",
    "TCS",
    "INFY"
]
RISK_PER_TRADE = 100
BOT_TOKEN = "8848402982:AAEWKzGbzpbEhVIfIL4qwdXK5uFrRNfxJOY"
CHAT_ID = "952222198"
