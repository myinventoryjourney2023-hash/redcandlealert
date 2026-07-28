import os
import csv

LOG_FILE = "trades.csv"


def save_trade(
    symbol,
    signal,
    position,
    trigger,
    trade
):

    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="") as f:

        writer = csv.writer(f)

        if not file_exists:

            writer.writerow([
                "Date",
                "Stock",
                "Entry",
                "SL",
                "Target1",
                "Target2",
                "Quantity",
                "Trigger Time",
                "Status"
            ])

        writer.writerow([
            str(trigger["trigger_time"]).split()[0],
            symbol,
            round(signal["entry"], 2),
            round(signal["sl"], 2),
            position["target1"],
            position["target2"],
            position["quantity"],
            trigger["trigger_time"],
            trade["status"]
        ])
