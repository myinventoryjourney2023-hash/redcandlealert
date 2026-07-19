import os
import time
import math
import logging
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import pandas as pd
import yfinance as yf

from flask import Flask


# ======================================================
# FLASK APP
# ======================================================

app = Flask(__name__)

@app.route("/")
def home():
    return "Red Candle Alert Bot Running"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ======================================================
# TIMEZONE
# ======================================================

IST = ZoneInfo("Asia/Kolkata")


def ist_now():
    return datetime.now(IST)


# ======================================================
# TELEGRAM
# ======================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


# ======================================================
# SETTINGS
# ======================================================

TIMEFRAME = "5m"
PERIOD = "2d"

ENTRY_BUFFER = 0.0015
SL_BUFFER = 0.0015

RISK_PER_TRADE = 200

SCAN_INTERVAL = 60

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)

MAX_ALERT_MEMORY = 1000


# ======================================================
# LOGGER
# ======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ======================================================
# MEMORY
# ======================================================

sent_alerts = {}

# ======================================================
# TELEGRAM
# ======================================================

def send_telegram(message):

    try:

        response = requests.post(
            TELEGRAM_URL,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=30
        )

        response.raise_for_status()

        logger.info("Telegram Alert Sent")

        return True

    except Exception as e:

        logger.error(f"Telegram Error : {e}")

        return False


# ======================================================
# STOCK LOADER
# ======================================================

def load_stocks(filename="stocks.txt"):

    try:

        stocks = []

        with open(filename, "r") as f:

            for line in f:

                symbol = line.strip().upper()

                if symbol:

                    stocks.append(symbol)

        logger.info(f"{len(stocks)} Symbols Loaded")

        return stocks

    except FileNotFoundError:

        logger.error("stocks.txt not found")

        return []

    except Exception as e:

        logger.error(f"Stock Loader Error : {e}")

        return []


# ======================================================
# SYMBOL TYPE
# ======================================================

def is_crypto(symbol):

    return symbol.upper() == "BTC-USD"


# ======================================================
# MARKET HOURS
# ======================================================

def is_market_open():

    now = ist_now()

    if now.weekday() >=
# ======================================================
# STRATEGY
# ======================================================

def check_signal(symbol):

    df = download_data(symbol)

    if df is None:
        return None

    try:

        # Need at least 3 completed candles
        if len(df) < 3:

            logger.info(f"{symbol} : Not enough candles")

            return None

        # Last completed candle
        candle = df.iloc[-2]

        # Previous completed candle
        previous = df.iloc[-3]

        # Candle Time
        candle_time = df.index[-2]

        if candle_time.tzinfo is not None:

            candle_time = candle_time.tz_convert(IST)

        else:

            candle_time = candle_time.tz_localize("UTC").tz_convert(IST)

        # NSE → Today's candle only
        if not is_crypto(symbol):

            if candle_time.date() != ist_now().date():

                logger.info(f"{symbol} : Old candle skipped")

                return None

        # -----------------------------
        # OHLC
        # -----------------------------

        open_price = float(candle["Open"])
        high_price = float(candle["High"])
        low_price = float(candle["Low"])
        close_price = float(candle["Close"])

        volume = int(candle["Volume"])
        previous_volume = int(previous["Volume"])

        # -----------------------------
        # CONDITION 1
        # RED CANDLE
        # -----------------------------

        if close_price >= open_price:

            logger.info(f"{symbol} : Green Candle")

            return None

        # -----------------------------
        # CONDITION 2
        # LOWER VOLUME
        # -----------------------------

        if volume >= previous_volume:

            logger.info(f"{symbol} : Volume Condition Failed")

            return None

        # -----------------------------
        # ENTRY
        # -----------------------------

        entry = round(
            high_price * (1 + ENTRY_BUFFER),
            2
        )

        # -----------------------------
        # STOP LOSS
        # -----------------------------

        sl = round(
            low_price * (1 - SL_BUFFER),
            2
        )

        risk = round(entry - sl, 2)

        if risk <= 0:

            logger.info(f"{symbol} : Invalid Risk")

            return None

        # -----------------------------
        # POSITION SIZE
        # -----------------------------

        qty = math.floor(
            RISK_PER_TRADE / risk
        )

        if qty < 1:
            qty = 1

        # -----------------------------
        # TARGETS
        # -----------------------------

        target1 = round(entry + risk, 2)

        target2 = round(entry + (2 * risk), 2)

        return {

            "symbol": symbol,

            "time": candle_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),

            "volume": volume,
            "previous_volume": previous_volume,

            "entry": entry,
            "sl": sl,

            "risk": risk,

            "qty": qty,

            "target1": target1,
            "target2": target2

        }

    except Exception as e:

        logger.error(
            f"{symbol} : Strategy Error : {e}"
        )

        return None

# ======================================================
# DUPLICATE ALERT
# ======================================================

def is_duplicate(signal):

    key = (
        signal["symbol"],
        signal["time"]
    )

    if key in sent_alerts:
        return True

    sent_alerts[key] = time.time()

    while len(sent_alerts) > MAX_ALERT_MEMORY:

        oldest = min(
            sent_alerts,
            key=sent_alerts.get
        )

        del sent_alerts[oldest]

    return False


# ======================================================
# TELEGRAM MESSAGE
# ======================================================

def build_message(signal):

    return (
        "🔴 RED CANDLE ALERT\n\n"

        f"Stock : {signal['symbol']}\n"
        f"Time : {signal['time']}\n\n"

        f"Open : {signal['open']}\n"
        f"High : {signal['high']}\n"
        f"Low : {signal['low']}\n"
        f"Close : {signal['close']}\n\n"

        f"Current Volume : {signal['volume']}\n"
        f"Previous Volume : {signal['previous_volume']}\n\n"

        f"Buy Above : {signal['entry']}\n"
        f"Stop Loss : {signal['sl']}\n\n"

        f"Risk / Share : {signal['risk']}\n"
        f"Quantity : {signal['qty']}\n\n"

        f"Target 1 : {signal['target1']}\n"
        f"Target 2 : {signal['target2']}"
    )


# ======================================================
# PROCESS SYMBOL
# ======================================================

def process_symbol(symbol):

    try:

        logger.info(f"Checking : {symbol}")

        signal = check_signal(symbol)

        if signal is None:
            return

        if is_duplicate(signal):

            logger.info(f"{symbol} : Duplicate Alert")

            return

        message = build_message(signal)

        send_telegram(message)

    except Exception as e:

        logger.exception(f"{symbol} : {e}")


# ======================================================
# MAIN LOOP
# ======================================================

def run_bot():

    logger.info("=" * 60)
    logger.info("RED CANDLE BOT STARTED")
    logger.info("=" * 60)

    stocks = load_stocks()

    if not stocks:

        logger.error("No Stocks Found")

        return

    while True:

        try:

            if ist_now().weekday() >= 5:

                logger.info("Weekend")

                for symbol in stocks:

                    if is_crypto(symbol):

                        process_symbol(symbol)

                        time.sleep(2)

                time.sleep(SCAN_INTERVAL)

                continue
