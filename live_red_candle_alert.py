from flask import Flask
from threading import Thread
import os
import time
import math
from datetime import datetime
from zoneinfo import ZoneInfo

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

BOT_TOKEN = "8780999788:AAHQXATRD8OWFKenIhjq97Gk3Q4QpTyGh9U"
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
            now = datetime.now(ZoneInfo("Asia/Kolkata"))
            print("Current IST Time:", now.strftime("%Y-%m-%d %H:%M:%S"))

            if now.hour < 8:
                print("Waiting For Market Open...")
                time.sleep(60)
                continue

            if now.hour > 12 or (now.hour == 12 and now.minute > 30):
                print("Market Closed")
                time.sleep(300)
                continue

            stocks = load_stocks()
            print(f"Scanning {len(stocks)} Stocks...")

            for stock in stocks:
                try:
                    print("Checking :", stock)
                    df=yf.download(stock,period="2d",interval="5m",progress=False,auto_adjust=False)
                    if df.empty or len(df)<3:
                        continue
                    if hasattr(df.columns,"nlevels") and df.columns.nlevels>1:
                        df.columns=df.columns.get_level_values(0)
                    last=df.iloc[-2]
                    prev=df.iloc[-3]
                    if last.name.date()!=now.date():
                        continue
                    ctime=str(last.name)
                    if last_alert_time.get(stock)==ctime:
                        continue
                    if last["Close"]<last["Open"] and last["Volume"]<prev["Volume"]:
                        entry=float(last["High"])
                        stop_loss=float(last["Low"])
                        sl=entry-stop_loss
                        if sl<=0: continue
                        qty=max(1,math.floor(MAX_RISK/sl))
                        t1=entry+sl
                        t2=entry+2*sl
                        msg=f"🔴 RED CANDLE ALERT\n\nStock : {stock}\nTime : {ctime}\n\nBuy Above : {entry:.2f}\nStop Loss : {stop_loss:.2f}\nQuantity : {qty}\nTarget 1 : {t1:.2f}\nTarget 2 : {t2:.2f}"
                        print(msg)
                        send(msg)
                        last_alert_time[stock]=ctime
                except Exception as e:
                    print(stock,"Error:",e)
            wait=300-((now.minute%5)*60+now.second)
            if wait<=0: wait=5
            time.sleep(wait)
        except Exception as e:
            print("MAIN ERROR:",e)
            time.sleep(60)

# ==========================
# START BOT
# ==========================

if __name__ == "__main__":

    Thread(target=run_bot, daemon=True).start()

    run_web()


