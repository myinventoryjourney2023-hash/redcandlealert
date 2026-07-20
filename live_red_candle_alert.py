from flask import Flask
from threading import Thread
import os
import time
import math
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

import yfinance as yf
import requests

# ==========================
# FLASK (Render)
# ==========================

app = Flask(__name__)

@app.route("/")
def home():
    return "Trading Bot Running Successfully"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ==========================
# TELEGRAM
# ==========================

BOT_TOKEN = "8848402982:AAEWKzGbzpbEhVIfIL4qwdXK5uFrRNfxJOY"
CHAT_ID = "952222198"

# ==========================
# SETTINGS
# ==========================

MAX_RISK = 200

last_alert_time = {}

# ==========================
# LOAD STOCKS
# ==========================

def load_stocks():
    with open("stocks.txt", "r") as f:
        return [x.strip().upper() for x in f if x.strip()]

# ==========================
# TELEGRAM SEND
# ==========================

def send(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=20
        )

    except Exception as e:
        print("Telegram Error :", e)

print("=" * 50)
print("LIVE RED CANDLE ALERT BOT")
print("=" * 50)

# ==========================
# MAIN BOT
# ==========================

def run_bot():

    while True:

        try:

            now = datetime.now(IST)

            # Market Time 9:20 AM - 03:30 PM

            if now.hour < 9 or (now.hour == 9 and now.minute < 20):
                print("Waiting For Market Open...")
                time.sleep(60)
                continue

            if now.hour > 15 or (now.hour == 15 and now.minute > 30):
                print("Market Closed")
                time.sleep(300)
                continue

            stocks = load_stocks()

            if len(stocks) == 0:
                print("stocks.txt Empty")
                time.sleep(60)
                continue

            print(f"\nScanning {len(stocks)} Stocks...")

            for stock in stocks:

                try:

                    print("\nDownloading Market Data...")

all_data = yf.download(
    tickers=stocks,
    period="2d",
    interval="5m",
    group_by="ticker",
    threads=True,
    progress=False,
    auto_adjust=False
)

for stock in stocks:

    try:

        print(f"\nChecking : {stock}")

        if stock not in all_data:
            print("No Data")
            continue

        df = all_data[stock].dropna()

        if df.empty or len(df) < 3:
            print("No Data")
            continue

        # आपका बाकी का कोड यहीं से जैसा है वैसा ही रहेगा...
        last = df.iloc[-2]
        prev = df.iloc[-3]

                    last = df.iloc[-2]
                    prev = df.iloc[-3]

                    candle_time = str(last.name)

                    if last_alert_time.get(stock) == candle_time:
                        print("Already Alert Sent")
                        continue
                                        # ==========================
                    # RED CANDLE + LOW VOLUME
                    # ==========================

                    if (
                        last["Close"] < last["Open"]
                        and last["Volume"] < prev["Volume"]
                    ):

                        entry = float(last["High"])
                        stop_loss = float(last["Low"])

                        sl_size = entry - stop_loss

                        if sl_size <= 0:
                            print("Invalid SL")
                            continue

                        qty = math.floor(MAX_RISK / sl_size)

                        if qty <= 0:
                            qty = 1

                        target1 = entry + sl_size
                        target2 = entry + (2 * sl_size)

                        message = (
                            f"🔴 RED CANDLE ALERT\n\n"
                            f"Stock : {stock}\n"
                            f"Time : {candle_time}\n\n"
                            f"Open : {last['Open']:.2f}\n"
                            f"High : {last['High']:.2f}\n"
                            f"Low : {last['Low']:.2f}\n"
                            f"Close : {last['Close']:.2f}\n\n"
                            f"Current Volume : {int(last['Volume'])}\n"
                            f"Previous Volume : {int(prev['Volume'])}\n\n"
                            f"Buy Above : {entry:.2f}\n"
                            f"Stop Loss : {stop_loss:.2f}\n"
                            f"SL Size : {sl_size:.2f}\n\n"
                            f"Risk : ₹{MAX_RISK}\n"
                            f"Quantity : {qty}\n\n"
                            f"Target 1 : {target1:.2f}\n"
                            f"Target 2 : {target2:.2f}"
                        )

                        print(message)

                        send(message)

                        last_alert_time[stock] = candle_time

                    else:

                        print(
                            f"{stock} | "
                            f"Red={last['Close'] < last['Open']} | "
                            f"LowVolume={last['Volume'] < prev['Volume']}"
                        )

                except Exception as e:

                    print(f"{stock} Error :", e)
                    continue
                            # ==========================
            # WAIT FOR NEXT 5 MIN CANDLE
            # ==========================

            now = datetime.now()

            wait_seconds = 300 - ((now.minute % 5) * 60 + now.second)

            if wait_seconds <= 0:
                wait_seconds = 5

            print(f"\nWaiting {wait_seconds} seconds...\n")

            time.sleep(wait_seconds)

        except Exception as e:

            print("MAIN ERROR :", e)

            time.sleep(60)


# ==========================
# START BOT
# ==========================

if __name__ == "__main__":

    print("RUN BOT STARTED")


    Thread(target=run_bot, daemon=True).start()

    run_web()


