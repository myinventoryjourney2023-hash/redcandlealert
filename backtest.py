"""
FYERS 1-minute backtest for the current Inside Strategy.

IMPORTANT:
- This is a SEPARATE backtest file. bot.py is not changed.
- Uses FYERS History API.
- Automatically finds the most recent N trading dates.
- Default: 12 trading days.
- Default: 1-minute candles.
- Strategy rules mirror the current Pine logic as closely as possible.

Environment variables:
    FYERS_APP_ID=...
    FYERS_ACCESS_TOKEN=...
    BACKTEST_DAYS=12
    RISK_AMOUNT=50
    BUY_BUFFER_PCT=0.02
    SL_BUFFER_PCT=0.02
    MAX_TRADES_PER_DAY=3
    BACKTEST_START=YYYY-MM-DD   (optional)
    BACKTEST_END=YYYY-MM-DD     (optional)

Run:
    python backtest.py
"""

import os
import math
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")

FYERS_APP_ID = os.getenv("FYERS_APP_ID", "")
FYERS_ACCESS_TOKEN = os.getenv("FYERS_ACCESS_TOKEN", "")

DAYS = int(os.getenv("BACKTEST_DAYS", "12"))
RISK_AMOUNT = float(os.getenv("RISK_AMOUNT", "50"))
BUY_BUFFER_PCT = float(os.getenv("BUY_BUFFER_PCT", "0.02"))
SL_BUFFER_PCT = float(os.getenv("SL_BUFFER_PCT", "0.02"))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", "3"))

START_ENV = os.getenv("BACKTEST_START", "")
END_ENV = os.getenv("BACKTEST_END", "")

FYERS_HISTORY_URL = "https://api-t1.fyers.in/data/history"

# Change these only if you want a different list for backtest.
STOCKS_FILE = os.getenv("STOCKS_FILE", "stocks.txt")


@dataclass
class Trade:
    symbol: str
    trade_no: int
    setup_time: str
    entry_time: str
    entry: float
    sl: float
    target: float
    qty: int
    risk_per_share: float
    result: str
    exit_price: float
    pnl: float


def read_stocks():
    path = STOCKS_FILE
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")

    result = []
    for line in open(path, encoding="utf-8"):
        s = line.strip().upper()
        if not s or s.startswith("#"):
            continue

        # Accept:
        # RELIANCE
        # RELIANCE.NS
        # NSE:RELIANCE-EQ
        if s.startswith("NSE:"):
            result.append(s)
        else:
            s = s.replace(".NS", "")
            result.append(f"NSE:{s}-EQ")

    return result


def get_trading_dates(end_date: date, count: int):
    dates = []
    d = end_date

    while len(dates) < count:
        # Monday-Friday. Exchange holidays are filtered later
        # because FYERS will return no candles for those dates.
        if d.weekday() < 5:
            dates.append(d)
        d -= timedelta(days=1)

    return list(reversed(dates))


def fetch_day(symbol: str, day: date) -> pd.DataFrame:
    if not FYERS_APP_ID or not FYERS_ACCESS_TOKEN:
        raise RuntimeError(
            "Set FYERS_APP_ID and FYERS_ACCESS_TOKEN first."
        )

    payload = {
        "symbol": symbol,
        "resolution": "1",
        "date_format": "1",
        "range_from": day.isoformat(),
        "range_to": day.isoformat(),
        "cont_flag": "1",
    }

    headers = {
        "Authorization": f"{FYERS_APP_ID}:{FYERS_ACCESS_TOKEN}"
    }

    r = requests.get(
        FYERS_HISTORY_URL,
        params=payload,
        headers=headers,
        timeout=20,
    )

    r.raise_for_status()
    data = r.json()

    if data.get("s") != "ok":
        raise RuntimeError(
            f"FYERS error for {symbol} {day}: {data}"
        )

    rows = data.get("candles", [])

    if not rows:
        return pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

    df = pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ],
    )

    # FYERS timestamps represent the START of the candle.
    # Convert epoch -> IST for reporting/simulation.
    df["timestamp"] = pd.to_datetime(
        df["timestamp"], unit="s", utc=True
    ).dt.tz_convert(IST)

    # Only regular NSE session.
    df = df[
        (df["timestamp"].dt.time >= datetime.strptime("09:15", "%H:%M").time())
        & (df["timestamp"].dt.time < datetime.strptime("15:30", "%H:%M").time())
    ].copy()

    return df.reset_index(drop=True)


def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def calculate_setup(previous, current):
    green_prev = previous["close"] > previous["open"]
    red_candle = current["close"] < current["open"]
    low_volume = current["volume"] < previous["volume"]
    inside_bar = (
        current["high"] < previous["high"]
        and current["low"] >= previous["low"]
    )

    if not (green_prev and red_candle and low_volume and inside_bar):
        return None

    setup_high = float(previous["high"])
    setup_low = float(current["low"])

    buy = setup_high * (1 + BUY_BUFFER_PCT / 100)
    sl = setup_low * (1 - SL_BUFFER_PCT / 100)

    risk = buy - sl
    if risk <= 0:
        return None

    raw_qty = math.floor(RISK_AMOUNT / risk)
    qty = 2 if raw_qty <= 1 else raw_qty

    target = buy + risk * 2

    return {
        "setup_high": setup_high,
        "setup_low": setup_low,
        "buy": buy,
        "sl": sl,
        "risk": risk,
        "qty": qty,
        "target": target,
    }


def simulate_symbol(symbol, df):
    """
    State machine based on the current Pine strategy.

    Important execution assumption:
    - A setup is formed from a completed candle.
    - Its stop-entry becomes active only from the NEXT candle.
    - If entry is reached, fill = buy price.
    - After entry, SL/target are monitored.
    - If both SL and target are touched in the SAME 1-minute candle,
      OHLC cannot reveal which happened first. We use a conservative
      SL-first assumption and mark it in the trade result.
    - After target hit, the position stays open and the day freezes.
    """

    trades = []

    state = "IDLE"
    setup = None
    trades_today = 0
    target_hit = False
    position_open = False
    entry_price = None

    # Process only completed candles.
    for i in range(1, len(df)):
        previous = df.iloc[i - 1]
        current = df.iloc[i]

        # Once target is hit, freeze the rest of the day.
        if target_hit:
            continue

        # ------------------------------------------------
        # Manage open position FIRST
        # ------------------------------------------------
        if position_open and setup:
            high = float(current["high"])
            low = float(current["low"])

            hit_sl = low <= setup["sl"]
            hit_target = high >= setup["target"]

            if hit_sl or hit_target:
                # Ambiguous same-candle case.
                if hit_sl and hit_target:
                    result = "SL_AND_TARGET_SAME_CANDLE_SL_FIRST"
                    exit_price = setup["sl"]
                    pnl = (exit_price - entry_price) * setup["qty"]

                    trades[-1].result = result
                    trades[-1].exit_price = exit_price
                    trades[-1].pnl = pnl

                    position_open = False
                    state = "WAITING_REENTRY"
                    continue

                if hit_target:
                    # REQUIRED:
                    # Position remains OPEN.
                    # No SL/new entry/re-entry for rest of day.
                    target_hit = True
                    state = "TARGET_HIT"

                    trades[-1].result = "TARGET_1_2_HIT_POSITION_OPEN"
                    trades[-1].exit_price = setup["target"]
                    trades[-1].pnl = (
                        setup["target"] - entry_price
                    ) * setup["qty"]

                    # Do NOT set position_open=False.
                    continue

                if hit_sl:
                    trades[-1].result = "SL_HIT"
                    trades[-1].exit_price = setup["sl"]
                    trades[-1].pnl = (
                        setup["sl"] - entry_price
                    ) * setup["qty"]

                    position_open = False
                    state = "WAITING_REENTRY"
                    continue

        # ------------------------------------------------
        # No open position -> create setup
        # ------------------------------------------------
        if not position_open and state in {"IDLE", "WAITING", "WAITING_REENTRY"}:
            # After an SL, the current setup remains frozen.
            # A fresh setup is NOT created until a new setup condition
            # appears; this follows the intended Pine state flow.
            if state != "WAITING_REENTRY":
                new_setup = calculate_setup(previous, current)

                if new_setup:
                    setup = new_setup
                    setup["setup_time"] = current["timestamp"]
                    state = "WAITING"

            # ------------------------------------------------
            # Entry is allowed from the candle AFTER setup candle.
            # Because calculate_setup() used previous/current above,
            # the stop order is active for the next loop candle.
            # ------------------------------------------------

        # ------------------------------------------------
        # Entry
        # ------------------------------------------------
        if (
            not position_open
            and not target_hit
            and setup is not None
            and state in {"WAITING", "WAITING_REENTRY"}
            and trades_today < MAX_TRADES_PER_DAY
        ):
            # Do not allow the setup candle itself to fill.
            setup_ts = setup["setup_time"]
            if current["timestamp"] <= setup_ts:
                continue

            if float(current["high"]) >= setup["buy"]:
                trades_today += 1

                entry_price = setup["buy"]
                position_open = True
                state = "IN_TRADE"

                trades.append(
                    Trade(
                        symbol=symbol,
                        trade_no=trades_today,
                        setup_time=str(setup["setup_time"]),
                        entry_time=str(current["timestamp"]),
                        entry=entry_price,
                        sl=setup["sl"],
                        target=setup["target"],
                        qty=setup["qty"],
                        risk_per_share=setup["risk"],
                        result="OPEN",
                        exit_price=0.0,
                        pnl=0.0,
                    )
                )

                # If this same candle also reaches SL/target,
                # manage it now.
                high = float(current["high"])
                low = float(current["low"])

                hit_sl = low <= setup["sl"]
                hit_target = high >= setup["target"]

                if hit_sl and hit_target:
                    trades[-1].result = "SL_AND_TARGET_SAME_CANDLE_SL_FIRST"
                    trades[-1].exit_price = setup["sl"]
                    trades[-1].pnl = (
                        setup["sl"] - entry_price
                    ) * setup["qty"]
                    position_open = False
                    state = "WAITING_REENTRY"

                elif hit_target:
                    target_hit = True
                    state = "TARGET_HIT"
                    trades[-1].result = "TARGET_1_2_HIT_POSITION_OPEN"
                    trades[-1].exit_price = setup["target"]
                    trades[-1].pnl = (
                        setup["target"] - entry_price
                    ) * setup["qty"]

                elif hit_sl:
                    trades[-1].result = "SL_HIT"
                    trades[-1].exit_price = setup["sl"]
                    trades[-1].pnl = (
                        setup["sl"] - entry_price
                    ) * setup["qty"]
                    position_open = False
                    state = "WAITING_REENTRY"

    return trades


def run():
    print("=" * 70)
    print("FYERS 1-MINUTE INSIDE STRATEGY BACKTEST")
    print("=" * 70)

    if START_ENV and END_ENV:
        start = date.fromisoformat(START_ENV)
        end = date.fromisoformat(END_ENV)

        dates = []
        d = start
        while d <= end:
            if d.weekday() < 5:
                dates.append(d)
            d += timedelta(days=1)
    else:
        dates = get_trading_dates(
            datetime.now(IST).date(),
            DAYS,
        )

    symbols = read_stocks()

    print(f"Period: {dates[0]} -> {dates[-1]}")
    print(f"Trading dates requested: {len(dates)}")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Risk: ₹{RISK_AMOUNT}")
    print(f"Entry buffer: {BUY_BUFFER_PCT}%")
    print(f"SL buffer: {SL_BUFFER_PCT}%")
    print(f"Max trades/day: {MAX_TRADES_PER_DAY}")
    print()

    all_trades = []

    for symbol in symbols:
        print(f"Fetching {symbol}...")

        symbol_df = []

        for d in dates:
            try:
                day_df = fetch_day(symbol, d)

                if not day_df.empty:
                    symbol_df.append(day_df)

            except Exception as e:
                print(f"  ERROR {d}: {e}")

            # Be polite to API.
            time.sleep(0.15)

        if not symbol_df:
            print("  No data.")
            continue

        df = (
            pd.concat(symbol_df, ignore_index=True)
            .sort_values("timestamp")
            .drop_duplicates("timestamp")
            .reset_index(drop=True)
        )

        print(f"  Candles: {len(df)}")

        trades = simulate_symbol(symbol, df)
        all_trades.extend(trades)

        print(f"  Trades: {len(trades)}")

    if not all_trades:
        print("\nNo trades found.")
        return

    out = pd.DataFrame([t.__dict__ for t in all_trades])

    # Save complete trade list.
    out.to_csv("backtest_trades.csv", index=False)

    total_pnl = out["pnl"].sum()
    wins = (out["pnl"] > 0).sum()
    losses = (out["pnl"] < 0).sum()
    target_hits = out["result"].eq(
        "TARGET_1_2_HIT_POSITION_OPEN"
    ).sum()

    print()
    print("=" * 70)
    print("BACKTEST RESULT")
    print("=" * 70)
    print(f"Total trades : {len(out)}")
    print(f"Winning     : {wins}")
    print(f"Losing      : {losses}")
    print(f"Target hits : {target_hits}")
    print(f"Total P&L   : ₹{total_pnl:.2f}")

    if len(out):
        print(f"Win rate    : {wins / len(out) * 100:.2f}%")

    print()
    print(out.to_string(index=False))
    print()
    print("Saved: backtest_trades.csv")


if __name__ == "__main__":
    run()
