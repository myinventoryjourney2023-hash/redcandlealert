import os
import uuid
from datetime import datetime

import pandas as pd


ACTIVE_TRADES_FILE = "active_trades.csv"
TRADE_HISTORY_FILE = "trades.csv"


COLUMNS = [
    "trade_id",
    "symbol",
    "status",

    "entry",
    "sl",
    "target1",
    "target2",

    "quantity",
    "risk_per_share",

    "signal_time",
    "trigger_time",

    "entry_triggered",

    "target1_hit",
    "target2_hit",

    "target1_alert_sent",
    "target2_alert_sent",

    "entry_price",
    "exit_price",

    "entry_time",
    "exit_time",

    "exit_reason",

    "created_time",
    "updated_time"
]


# ===================================
# Utility
# ===================================

def now():

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_empty_csv(filename):

    if not os.path.exists(filename):

        pd.DataFrame(columns=COLUMNS).to_csv(
            filename,
            index=False
        )


create_empty_csv(ACTIVE_TRADES_FILE)
create_empty_csv(TRADE_HISTORY_FILE)


# ===================================
# Read Active Trades
# ===================================

def load_active_trades():

    create_empty_csv(ACTIVE_TRADES_FILE)

    df = pd.read_csv(ACTIVE_TRADES_FILE)

    if df.empty:
        return []

    return df.to_dict("records")


# ===================================
# Save Active Trades
# ===================================

def save_active_trades(trades):

    df = pd.DataFrame(trades)

    for col in COLUMNS:

        if col not in df.columns:
            df[col] = None

    df = df[COLUMNS]

    df.to_csv(
        ACTIVE_TRADES_FILE,
        index=False
    )


# ===================================
# Trade Exists?
# ===================================

def is_trade_open(symbol):

    trades = load_active_trades()

    for trade in trades:

        if (
            trade.get("symbol") == symbol
            and trade.get("status") == "OPEN"
        ):

            return True

    return False

# ===================================
# Generate Trade ID
# ===================================

def generate_trade_id():

    return uuid.uuid4().hex[:12]
# ===================================
# Create Trade
# ===================================

def create_trade(trade):

    trades = load_active_trades()

    # Duplicate protection
    for t in trades:

        if (
            t["symbol"] == trade["symbol"]
            and t["status"] == "OPEN"
        ):

            return None

    current_time = now()

    trade["trade_id"] = generate_trade_id()

    trade["status"] = "OPEN"

    trade["entry_triggered"] = True

    trade["target1_hit"] = False
    trade["target2_hit"] = False

    trade["target1_alert_sent"] = False
    trade["target2_alert_sent"] = False

    trade["entry_price"] = trade["entry"]
    trade["exit_price"] = None

    trade["entry_time"] = current_time
    trade["exit_time"] = None

    trade["exit_reason"] = None

    trade["created_time"] = current_time
    trade["updated_time"] = current_time

    trades.append(trade)

    save_active_trades(trades)

    return trade["trade_id"]


# ===================================
# Update Trade
# ===================================

def update_trade(symbol, **kwargs):

    trades = load_active_trades()

    updated = False

    for trade in trades:

        if (
            trade["symbol"] == symbol
            and trade["status"] == "OPEN"
        ):

            for key, value in kwargs.items():

                trade[key] = value

            trade["updated_time"] = now()

            updated = True

            break

    if updated:

        save_active_trades(trades)

    return updated


# ===================================
# Close Trade
# ===================================

def close_trade(symbol, exit_price, reason):

    trades = load_active_trades()

    history = []

    if os.path.exists(TRADE_HISTORY_FILE):

        history = pd.read_csv(
            TRADE_HISTORY_FILE
        ).to_dict("records")

    active = []

    for trade in trades:

        if (
            trade["symbol"] == symbol
            and trade["status"] == "OPEN"
        ):

            trade["status"] = "CLOSED"

            trade["exit_price"] = exit_price
            trade["exit_time"] = now()
            trade["exit_reason"] = reason
            trade["updated_time"] = now()

            history.append(trade)

        else:

            active.append(trade)

    save_active_trades(active)

    history_df = pd.DataFrame(history)

    for col in COLUMNS:

        if col not in history_df.columns:
            history_df[col] = None

    history_df = history_df[COLUMNS]

    history_df.to_csv(
        TRADE_HISTORY_FILE,
        index=False
    )

    return True
