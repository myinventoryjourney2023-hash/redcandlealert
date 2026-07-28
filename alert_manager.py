import csv
import os
from datetime import datetime

FILE_NAME = "alerts_sent.csv"


def can_send_alert(symbol, volume):

    today = str(datetime.now().date())

    data = {}

    if os.path.exists(FILE_NAME):

        with open(FILE_NAME, "r", newline="") as f:

            reader = csv.DictReader(f)

            for row in reader:

                if row["Date"] == today:

                    data[row["Symbol"]] = float(row["Volume"])

    if symbol not in data:

        data[symbol] = volume
        save_file(today, data)
        return True

    if volume < data[symbol]:

        data[symbol] = volume
        save_file(today, data)
        return True

    return False


def save_file(today, data):

    with open(FILE_NAME, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Date",
            "Symbol",
            "Volume"
        ])

        for symbol, volume in data.items():

            writer.writerow([
                today,
                symbol,
                volume
            ])
