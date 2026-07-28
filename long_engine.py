from strategy import run_long_strategy
from entry import check_entry_trigger
from position import calculate_position
from trade_manager import (
    create_trade,
    is_trade_open
)
from trade_log import save_trade
from telegram_bot import send_message
from alert_manager import can_send_alert


def run_long_engine(report):

    print("\n========== LONG STRATEGY ==========")

    for stock in report["gainers"]:

        symbol = stock["symbol"]

        print(f"\nChecking : {symbol}")

        if is_trade_open(symbol):
            print("Trade Already Open")
            continue

        signal = run_long_strategy(stock["data"])

        if signal is None:
            print("No Signal")
            continue

        print("Signal Found")

        trigger = check_entry_trigger(
            stock["data"],
            signal
        )

        if trigger is None:
            print("Entry Not Triggered")
            continue

        print("ENTRY TRIGGERED ✅")
        print(f"Trigger Time : {trigger['trigger_time']}")

        position = calculate_position(
            signal["entry"],
            signal["sl"]
        )

        if position is None:
            print("Position Error")
            continue

        print(f"Risk/Share : {position['risk_per_share']}")
        print(f"Quantity   : {position['quantity']}")
        print(f"Target 1   : {position['target1']}")
        print(f"Target 2   : {position['target2']}")

        trade = {
            "symbol": symbol,
            "status": "OPEN",

            "entry": signal["entry"],
            "sl": signal["sl"],

            "target1": position["target1"],
            "target2": position["target2"],

            "quantity": position["quantity"],
            "risk_per_share": position["risk_per_share"],

            "signal_time": signal.get("time"),
            "trigger_time": trigger["trigger_time"],

            "target1_hit": False,
            "target2_hit": False
        }

        create_trade(trade)

        message = f"""
🟢 LONG SIGNAL

Stock : {symbol}

Entry : {signal['entry']:.2f}
SL : {signal['sl']:.2f}

Quantity : {position['quantity']}

Target 1 : {position['target1']:.2f}
Target 2 : {position['target2']:.2f}

Trigger : {trigger['trigger_time']}
"""

        if can_send_alert(
            symbol,
            signal["volume"]
        ):
            send_message(message)
        else:
            print("Duplicate Alert Skipped")

        save_trade(
            symbol,
            signal,
            position,
            trigger,
            {
                "status": "OPEN",
                "time": None
            }
        )
