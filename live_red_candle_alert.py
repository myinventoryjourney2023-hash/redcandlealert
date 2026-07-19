from flask import Flask
from threading import Thread
import os,time,math
from datetime import datetime
from zoneinfo import ZoneInfo
import yfinance as yf
import requests

app=Flask(__name__)

@app.route("/")
def home():
    return "Trading Bot Running Successfully"

def run_web():
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))

BOT_TOKEN="8780999788:AAHQXATRD8OWFKenIhjq97Gk3Q4QpTyGh9U"
CHAT_ID="952222198"
MAX_RISK=200
last_alert_time={}

def load_stocks():
    with open("stocks.txt") as f:
        return [i.strip().upper() for i in f if i.strip()]

def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id":CHAT_ID,"text":msg},
            timeout=20)
    except Exception as e:
        print("Telegram Error:",e)

print("="*50)
print("LIVE RED CANDLE ALERT BOT")
print("="*50)

def run_bot():
    print("RUN BOT STARTED")
    while True:
        try:
            now=datetime.now(ZoneInfo("Asia/Kolkata"))
            print("Current IST Time:",now.strftime("%Y-%m-%d %H:%M:%S"))
            stocks=load_stocks()
            print(f"Scanning {len(stocks)} Stocks...")
            for stock in stocks:
                try:
                    print("Checking :",stock)
                    df=yf.download(stock,period="2d",interval="5m",progress=False,auto_adjust=False)
                    if df.empty or len(df)<3:
                        continue
                    if hasattr(df.columns,"nlevels") and df.columns.nlevels>1:
                        df.columns=df.columns.get_level_values(0)
                    last=df.iloc[-2]
                    prev=df.iloc[-3]
                    ctime=last.name
                    if getattr(ctime,"tzinfo",None):
                        ctime=ctime.tz_convert("Asia/Kolkata")
                    ctime=ctime.strftime("%Y-%m-%d %H:%M:%S IST")
                    if last_alert_time.get(stock)==ctime:
                        continue
                    if last["Close"]<last["Open"] and last["Volume"]<prev["Volume"]:
                        buffer=float(last["Close"])*0.0015
                        entry=float(last["High"])+buffer
                        sl=float(last["Low"])-buffer
                        risk=entry-sl
                        if risk<=0:
                            continue
                        qty=max(1,math.floor(MAX_RISK/risk))
                        t1=entry+risk
                        t2=entry+2*risk
                        msg=f"""🔴 RED CANDLE ALERT

Stock : {stock}
Time : {ctime}

Buy Above : {entry:.2f}
Stop Loss : {sl:.2f}
Quantity : {qty}
Target 1 : {t1:.2f}
Target 2 : {t2:.2f}"""
                        print(msg)
                        send(msg)
                        last_alert_time[stock]=ctime
                except Exception as e:
                    print(stock,"ERROR:",e)
            wait=300-((datetime.now(ZoneInfo("Asia/Kolkata")).minute%5)*60+datetime.now(ZoneInfo("Asia/Kolkata")).second)
            if wait<=0: wait=5
            time.sleep(wait)
        except Exception as e:
            print("MAIN ERROR:",e)
            time.sleep(60)

if __name__=="__main__":
    Thread(target=run_bot,daemon=True).start()
    run_web()
