# ==========================================
# SIMPLE LONG BOT
# FINAL VERSION
# PART 1
# ==========================================

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf


# ==========================================
# SETTINGS
# ==========================================

BOT_TOKEN = "8848402982:AAEWKzGbzpbEhVIfIL4qwdXK5uFrRNfxJOY"
CHAT_ID = "952222198"

RISK_AMOUNT = 100

ENTRY_BUFFER = 0.0010
SL_BUFFER = 0.0010

PERIOD = "2d"
INTERVAL = "5m"

TEST_MODE = False

IST = ZoneInfo("Asia/Kolkata")

triggered = {}


# ==========================================
# TELEGRAM
# ==========================================

def send_telegram(message):

    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )

    except Exception as e:

        print("Telegram Error :", e)


# ==========================================
# LOAD STOCKS
# ==========================================

def load_stocks():

    stocks = []

    with open("stocks.txt") as f:

        for line in f:

            line = line.strip().upper()

            if line != "":
                stocks.append(line)

    return stocks


# ==========================================
# DOWNLOAD DATA
# ==========================================

def get_data(symbol):

    try:

        df = yf.download(
            symbol + ".NS",
            period=PERIOD,
            interval=INTERVAL,
            progress=False,
            auto_adjust=False,
            group_by="column"
        )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[
            ["Open", "High", "Low", "Close", "Volume"]
        ].copy()

        df.dropna(inplace=True)

        return df

    except Exception as e:

        print(symbol, e)
        return None


# ==========================================
# MARKET TIME
# ==========================================

def market_open():

    if TEST_MODE:
        return True

    now = datetime.now(IST)

    if now.weekday() >= 5:
        return False

    minutes = now.hour * 60 + now.minute

    return 570 <= minutes <= 930


# ==========================================
# CHECK STOCK
# ==========================================

def check_stock(symbol):

    print("-" * 50)
    print(symbol)

    df = get_data(symbol)

    if df is None or df.empty:
        print("No Data")
        return

    today = df.index[-1].date()

    df = df[df.index.date == today]

    if not TEST_MODE:
        df = df.between_time("09:30", "15:30")

    if len(df) <= 3:
        print("Not Enough Candles")
        return

    lowest = None

    for i in range(3, len(df)):

        candle = df.iloc[i]

        if candle["Close"] >= candle["Open"]:
            continue

        if lowest is None:
            lowest = candle

        elif candle["Volume"] < lowest["Volume"]:
            lowest = candle

    if lowest is None:
        print("No Red Signal")
        return
    print("Signal Time :", lowest.name.strftime("%H:%M"))
    print("High        :", round(lowest["High"], 2))
    print("Low         :", round(lowest["Low"], 2))
    print("Volume      :", int(lowest["Volume"]))

    entry = round(lowest["High"] * (1 + ENTRY_BUFFER), 2)
    sl = round(lowest["Low"] * (1 - SL_BUFFER), 2)

    share_risk = round(entry - sl, 2)

    if share_risk <= 0:
        return

    qty = max(1, int(RISK_AMOUNT / share_risk))

    target1 = round(entry + share_risk, 2)
    target2 = round(entry + (2 * share_risk), 2)

    print("Entry       :", entry)
    print("SL          :", sl)
    print("Share Risk  :", share_risk)
    print("Quantity    :", qty)

    # ==========================================
    # LIVE HIGH BREAK CHECK
    # ==========================================

    signal_time = lowest.name

    # Latest completed candle
    if len(df) < 2:
        print("Waiting High Break")
        return

    latest = df.iloc[-2]

    # Signal candle ke baad ki candle honi chahiye
    if latest.name <= signal_time:
        print("Waiting High Break")
        return

    # Entry break nahi hua
    if latest["High"] < entry:
        print("Waiting High Break")
        return

    # Duplicate alert
    if symbol in triggered:
        return

    triggered[symbol] = True

    msg = f"""
🟢 LONG SIGNAL

Stock : {symbol}

Entry : {entry}
SL : {sl}

Share Risk : ₹{share_risk}
Risk Amount : ₹{RISK_AMOUNT}
Quantity : {qty}

Target 1 : {target1}
Target 2 : {target2}

Trigger : {latest.name.strftime('%Y-%m-%d %H:%M')}
"""

    print(msg)

    send_telegram(msg)



# ==========================================
# START
# ==========================================

last_reset_date = None

if __name__ == "__main__":

    try:

        while True:

            today = datetime.now(IST).date()

            # ==========================================
            # DAILY RESET (एक बार प्रति दिन)
            # ==========================================

            if last_reset_date != today:

                triggered.clear()

                last_reset_date = today

                print()
                print("=" * 50)
                print("NEW TRADING DAY")
                print("Triggered List Reset")
                print("=" * 50)
                print()

            if not market_open():

                print(
                    "Market Closed :",
                    datetime.now(IST).strftime("%d-%m-%Y %H:%M:%S")
                )

                time.sleep(60)
                continue

            stocks = load_stocks()

            print()
            print("=" * 50)
            print("Scanning :", datetime.now(IST).strftime("%H:%M:%S"))
            print("=" * 50)

            for stock in stocks:

                check_stock(stock)

            print()
            print("Waiting 30 Seconds...")
            print()

            time.sleep(30)

    except KeyboardInterrupt:

        print()
        print("Bot Stopped By User")
