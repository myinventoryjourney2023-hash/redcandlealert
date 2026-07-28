import yfinance as yf
import pandas as pd

from stock_lists import get_stock_list
from config import TOP_GAINERS, TOP_LOSERS

def scan_market():

    stocks = get_stock_list()

    results = []

    print(f"Scanning {len(stocks)} stocks...\n")

    for stock in stocks:

        try:

            symbol = stock + ".NS"

            df = yf.download(
                symbol,
                period="1d",
                interval="5m",
                progress=False,
                auto_adjust=False,
                multi_level_index=False
            )

            if df.empty:
                continue

            day_open = float(df["Open"].iloc[0])
            current = float(df["Close"].iloc[-1])

            change = ((current - day_open) / day_open) * 100

            results.append({
                "Stock": stock,
                "Price": round(current, 2),
                "Change %": round(change, 2)
            })

        except Exception:
            pass

    df = pd.DataFrame(results)

    gainers = df.sort_values("Change %", ascending=False).head(TOP_GAINERS)

    losers = df.sort_values("Change %").head(TOP_LOSERS)

    return gainers, losers
