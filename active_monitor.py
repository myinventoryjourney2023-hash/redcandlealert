from trade_manager import (
    load_active_trades,
    update_trade,
    close_trade,
)

from telegram_bot import send_message


def monitor_active_trades(report):

    trades = load_active_trades()

    if not trades:
        print("\nNo Active Trades")
        return

    print(f"\nMonitoring {len(trades)} Active Trades")

    # ----------------------------------
    # Report से Symbol -> DataFrame Map
    # ----------------------------------

    stock_map = {}

    for stock in report["gainers"]:

        stock_map[stock["symbol"]] = stock["data"]

    # ----------------------------------
    # Check Every Open Trade
    # ----------------------------------

    for trade in trades:

        symbol = trade["symbol"]

        if symbol not in stock_map:

            continue

        df = stock_map[symbol]

        if len(df) < 2:

            continue

        # Last Completed Candle

        candle = df.iloc[-2]

        high = float(candle["High"])
        low = float(candle["Low"])

        target1 = float(trade["target1"])
        target2 = float(trade["target2"])
        sl = float(trade["sl"])

        print(f"\nChecking : {symbol}")
                # ----------------------------------
        # STOP LOSS
        # ----------------------------------

        if low <= sl:

            print("STOP LOSS HIT")

            close_trade(
                symbol=symbol,
                exit_price=sl,
                reason="STOP LOSS"
            )

            send_message(
f"""🔴 STOP LOSS HIT

Stock : {symbol}

Exit Price : {sl:.2f}

Trade Closed
"""
            )

            continue


        # ----------------------------------
        # TARGET 1
        # ----------------------------------

        target1_hit = str(trade.get("target1_hit", "False")).lower() == "true"
        target1_alert_sent = str(
            trade.get("target1_alert_sent", "False")
        ).lower() == "true"

        if (
            high >= target1
            and not target1_hit
        ):

            print("TARGET 1 HIT")

            update_trade(
                symbol,
                target1_hit=True,
                target1_alert_sent=True
            )

            if not target1_alert_sent:

                send_message(
f"""🟡 TARGET 1 HIT

Stock : {symbol}

Target 1 : {target1:.2f}
"""
                )


        # ----------------------------------
        # TARGET 2
        # ----------------------------------

        if high >= target2:

            print("TARGET 2 HIT")

            close_trade(
                symbol=symbol,
                exit_price=target2,
                reason="TARGET 2"
            )

            send_message(
f"""🟢 TARGET 2 HIT

Stock : {symbol}

Exit Price : {target2:.2f}

Trade Closed
"""
            )

            continue

        print("Trade Active")
        
