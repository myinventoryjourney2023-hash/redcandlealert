import yfinance as yf
import requests
import time
import math
from datetime import datetime

# ==========================
# TELEGRAM
# ==========================

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# ==========================
# SETTINGS
# ==========================

MAX_RISK = 200

# ==========================
# LOAD STOCK LIST
# ==========================

def load_stocks():
    with open("stocks.txt", "r") as f:
        return [line.strip().upper() for line in f if line.strip()]

# ==========================
# TELEGRAM FUNCTION
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

        print("Telegram Error:", e)

# ==========================
# ALERT MEMORY
# ==========================

last_alert_time = {}

print("=" * 50)
print("LIVE MULTI STOCK ALERT BOT STARTED")
print("=" * 50)

# ==========================
# START LOOP
# ==========================

while True:

    try:

        now = datetime.now()

        # MARKET TIME
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            print("Waiting for Market Open...")
            time.sleep(60)
            continue

        if now.hour > 12 or (now.hour == 12 and now.minute > 30):
            print("Market Closed for Strategy")
            time.sleep(300)
            continue

        # Load today's stock list
        stocks = load_stocks()

        if len(stocks) == 0:
            print("stocks.txt is empty")
            time.sleep(60)
            continue

        # Scan Every Stock
        for stock in stocks:

            print(f"\nChecking : {stock}")

            df = yf.download(
                stock,
                period="2d",
                interval="5m",
                progress=False,
                auto_adjust=False
            )

            # Remove MultiIndex
            if hasattr(df.columns, "nlevels"):
                if df.columns.nlevels > 1:
                    df.columns = df.columns.get_level_values(0)

            if len(df) < 3:
                print("No Data")
                continue

            last = df.iloc[-2]
            prev = df.iloc[-3]

            candle_time = str(last.name)

            # Duplicate Alert Stop
            if last_alert_time.get(stock) == candle_time:
                print("Already Alert Sent")
                continue

                        # ==========================
            # RED CANDLE + LOW VOLUME
            # ==========================

            if last["Close"] < last["Open"] and last["Volume"] < prev["Volume"]:

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

                        # ==========================
        # WAIT FOR NEXT 5 MIN CANDLE
        # ==========================

        now = datetime.now()

        wait_seconds = 300 - ((now.minute % 5) * 60 + now.second)

        if wait_seconds <= 0:
            wait_seconds = 5

        print(f"\nWaiting {wait_seconds} seconds for next candle...\n")

        time.sleep(wait_seconds)

    except Exception as e:

        print("ERROR :", e)

        time.sleep(60)
