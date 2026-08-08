import os
import time
import math
import logging
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
from threading import Thread, Lock

import pandas as pd
import requests
import yfinance as yf
from flask import Flask, jsonify

IST = ZoneInfo("Asia/Kolkata")

# ============================================================
# CONFIG
# ============================================================

TIMEFRAME = os.getenv("TIMEFRAME", "1m")
PERIOD = os.getenv("PERIOD", "2d")

RISK_AMOUNT = float(os.getenv("RISK_AMOUNT", "50"))
BUY_BUFFER_PCT = float(os.getenv("BUY_BUFFER_PCT", "0.02"))
SL_BUFFER_PCT = float(os.getenv("SL_BUFFER_PCT", "0.02"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "3"))

MARKET_START = dt_time(9, 15)
MARKET_END = dt_time(15, 5)

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))

# Keep TRUE until broker execution is connected and tested.
PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

STOCKS_FILE = os.getenv("STOCKS_FILE", "stocks.txt")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("inside-bot")

# ============================================================
# WEB SERVICE HEALTH ENDPOINT
# ============================================================

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({
        "service": "inside-strategy-bot",
        "status": "running",
        "timeframe": TIMEFRAME,
        "paper_mode": PAPER_MODE
    })

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

# ============================================================
# STATE
# ============================================================

@dataclass
class TradeState:
    state: str = "IDLE"
    setup_high: float | None = None
    setup_low: float | None = None
    buy_price: float | None = None
    sl_price: float | None = None
    risk_per_share: float | None = None
    qty: int = 0
    target_price: float | None = None
    setup_timestamp: pd.Timestamp | None = None
    trades_today: int = 0
    target_hit: bool = False
    entry_pending: bool = False
    position_open: bool = False
    entry_price: float | None = None

states: dict[str, TradeState] = {}
state_lock = Lock()
current_day = None

# ============================================================
# TELEGRAM
# ============================================================

def telegram(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        log.info("Telegram not configured:\n%s", message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": message},
            timeout=10,
        )
    except Exception:
        log.exception("Telegram send failed")

# ============================================================
# STOCK LIST
# ============================================================

def load_stocks() -> list[str]:
    path = Path(STOCKS_FILE)
    if not path.exists():
        return []

    symbols = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        symbol = line.upper()
        if not symbol.endswith(".NS"):
            symbol += ".NS"
        symbols.append(symbol)

    return symbols

# ============================================================
# MARKET DATA
# ============================================================

def fetch_data(symbol: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        period=PERIOD,
        interval=TIMEFRAME,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close", "Volume"]
    df = df.dropna(subset=required)
    return df

# ============================================================
# HELPERS
# ============================================================

def market_open_now() -> bool:
    now = datetime.now(IST).time()
    return MARKET_START <= now < MARKET_END

def reset_for_new_day() -> None:
    with state_lock:
        for state in states.values():
            state.state = "IDLE"
            state.setup_high = None
            state.setup_low = None
            state.buy_price = None
            state.sl_price = None
            state.risk_per_share = None
            state.qty = 0
            state.target_price = None
            state.setup_timestamp = None
            state.trades_today = 0
            state.target_hit = False
            state.entry_pending = False
            state.position_open = False
            state.entry_price = None

def update_day() -> None:
    global current_day
    today = datetime.now(IST).date()

    if current_day is None:
        current_day = today
        return

    if today != current_day:
        reset_for_new_day()
        current_day = today
        log.info("New trading day: state reset")

def get_state(symbol: str) -> TradeState:
    with state_lock:
        if symbol not in states:
            states[symbol] = TradeState()
        return states[symbol]

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")

# ============================================================
# STRATEGY
# ============================================================

def check_setup(symbol: str, df: pd.DataFrame, state: TradeState) -> None:
    if len(df) < 4:
        return

    # Pine completed-candle behavior:
    # current = last completed candle, previous = candle before it.
    current = df.iloc[-2]
    previous = df.iloc[-3]

    if state.target_hit or state.position_open:
        return

    if state.trades_today >= MAX_TRADES_PER_DAY:
        return

    green_prev = previous["Close"] > previous["Open"]
    red_candle = current["Close"] < current["Open"]
    low_volume = current["Volume"] < previous["Volume"]
    inside_bar = (
        current["High"] < previous["High"]
        and current["Low"] >= previous["Low"]
    )

    if not (green_prev and red_candle and low_volume and inside_bar):
        return

    if (
        state.setup_timestamp is not None
        and state.setup_timestamp == current.name
        and state.state in {"WAITING", "WAITING_REENTRY"}
    ):
        return

    state.setup_high = float(previous["High"])
    state.setup_low = float(current["Low"])
    state.setup_timestamp = current.name

    state.buy_price = state.setup_high * (1 + BUY_BUFFER_PCT / 100)
    state.sl_price = state.setup_low * (1 - SL_BUFFER_PCT / 100)
    state.risk_per_share = state.buy_price - state.sl_price

    if state.risk_per_share <= 0:
        return

    calculated_qty = math.floor(RISK_AMOUNT / state.risk_per_share)
    state.qty = 2 if calculated_qty <= 1 else calculated_qty

    state.target_price = state.buy_price + state.risk_per_share * 2
    state.target_hit = False

    if state.state != "WAITING_REENTRY":
        state.state = "WAITING"

    state.entry_pending = True

    log.info(
        "%s | SETUP | entry=%.4f sl=%.4f target=%.4f qty=%d",
        symbol, state.buy_price, state.sl_price,
        state.target_price, state.qty
    )

    telegram(
        f"🟢 LONG SETUP\n"
        f"📈 {symbol}\n"
        f"💰 Entry: {state.buy_price:.4f}\n"
        f"🛑 SL: {state.sl_price:.4f}\n"
        f"🎯 TG 1:2: {state.target_price:.4f}\n"
        f"📦 Qty: {state.qty}\n"
        f"⚠️ Risk/share: ₹{state.risk_per_share:.4f}\n"
        f"💰 Total risk: ₹{state.risk_per_share * state.qty:.2f}"
    )

def check_entry(symbol: str, df: pd.DataFrame, state: TradeState) -> None:
    if state.target_hit or state.position_open:
        return

    if state.state not in {"WAITING", "WAITING_REENTRY"}:
        return

    if not state.entry_pending or state.buy_price is None:
        return

    candle = df.iloc[-2]

    if float(candle["High"]) < state.buy_price:
        return

    state.position_open = True
    state.entry_pending = False
    state.entry_price = state.buy_price
    state.trades_today += 1
    state.state = "IN_TRADE"

    entry_no = ordinal(state.trades_today)

    log.info(
        "%s | ENTRY %s | entry=%.4f sl=%.4f target=%.4f qty=%d",
        symbol, entry_no, state.entry_price,
        state.sl_price, state.target_price, state.qty
    )

    telegram(
        f"🟢 LONG ENTRY {entry_no}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 Stock: {symbol}\n"
        f"💰 Entry: {state.entry_price:.4f}\n"
        f"🛑 Stop Loss: {state.sl_price:.4f}\n"
        f"🎯 Target 1:2: {state.target_price:.4f}\n"
        f"📦 Quantity: {state.qty}\n"
        f"⚠️ Risk/share: ₹{state.risk_per_share:.4f}\n"
        f"💰 Total Risk: ₹{state.risk_per_share * state.qty:.2f}\n"
        f"📊 Trade: {state.trades_today}/{MAX_TRADES_PER_DAY}"
    )

def check_target(symbol: str, df: pd.DataFrame, state: TradeState) -> None:
    if state.state != "IN_TRADE" or not state.position_open:
        return

    if state.target_hit or state.target_price is None:
        return

    candle = df.iloc[-2]

    if float(candle["High"]) < state.target_price:
        return

    # REQUIRED FREEZE:
    # - position remains open
    # - SL is cancelled by broker adapter
    # - no new setup
    # - no new entry
    # - no re-entry
    # - no SL processing
    state.target_hit = True
    state.state = "TARGET_HIT"

    cancel_stop_loss(symbol)

    log.info(
        "%s | 🎯 TARGET 1:2 HIT | position remains OPEN | frozen",
        symbol
    )

    telegram(
        f"🎯 TARGET 1:2 HIT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 Stock: {symbol}\n"
        f"🎯 Target: {state.target_price:.4f}\n"
        f"🟢 Position remains OPEN\n"
        f"🔒 No new entry / re-entry / SL"
    )

def check_stop_loss(symbol: str, df: pd.DataFrame, state: TradeState) -> None:
    if state.target_hit:
        return

    if state.state != "IN_TRADE" or not state.position_open:
        return

    if state.sl_price is None:
        return

    candle = df.iloc[-2]

    if float(candle["Low"]) > state.sl_price:
        return

    state.position_open = False
    state.entry_pending = False
    state.state = "WAITING_REENTRY"

    log.info("%s | 🔴 SL HIT | re-entry allowed", symbol)

    telegram(
        f"🔴 INSIDE LONG STOP LOSS\n"
        f"📈 Stock: {symbol}\n"
        f"🛑 SL: {state.sl_price:.4f}\n"
        f"🔄 Re-entry allowed"
    )

# ============================================================
# BROKER PLACEHOLDER
# ============================================================

def cancel_stop_loss(symbol: str) -> None:
    if PAPER_MODE:
        return

    log.warning(
        "%s | LIVE broker adapter not connected yet: "
        "cancel_stop_loss()",
        symbol
    )

# ============================================================
# SYMBOL PROCESSOR
# ============================================================

def process_symbol(symbol: str) -> None:
    state = get_state(symbol)

    try:
        df = fetch_data(symbol)

        if df.empty:
            log.warning("%s | no market data", symbol)
            return

        # Target is checked first. After target hit, everything freezes.
        if state.position_open:
            check_target(symbol, df, state)

            if not state.target_hit:
                check_stop_loss(symbol, df, state)

        if not state.target_hit and not state.position_open:
            check_setup(symbol, df, state)
            check_entry(symbol, df, state)

    except Exception:
        log.exception("%s | processing error", symbol)

# ============================================================
# BOT LOOP
# ============================================================

def bot_loop() -> None:
    global current_day

    log.info("Inside Strategy Bot starting...")
    log.info("TIMEFRAME=%s PERIOD=%s", TIMEFRAME, PERIOD)
    log.info("PAPER_MODE=%s", PAPER_MODE)

    current_day = datetime.now(IST).date()

    while True:
        try:
            update_day()

            if not market_open_now():
                time.sleep(POLL_SECONDS)
                continue

            stocks = load_stocks()

            if not stocks:
                log.warning("stocks.txt is empty")
                time.sleep(POLL_SECONDS)
                continue

            for symbol in stocks:
                process_symbol(symbol)

            time.sleep(POLL_SECONDS)

        except Exception:
            log.exception("Bot loop error")
            time.sleep(POLL_SECONDS)

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    worker = Thread(target=bot_loop, daemon=True)
    worker.start()

    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
