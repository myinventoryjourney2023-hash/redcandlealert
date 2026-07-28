import os
import time
import pandas as pd

from config import SCAN_MODE
from nselib import capital_market

CACHE_FILE = "fo_list.csv"


def get_stock_list():

    if SCAN_MODE != "FO":
        return []

    # =========================
    # Try NSE First
    # =========================
    for attempt in range(3):

        try:

            data = capital_market.fno_equity_list()

            if hasattr(data, "columns"):

                if "symbol" in data.columns:
                    symbols = sorted(
                        data["symbol"].dropna().astype(str).tolist()
                    )

                elif "SYMBOL" in data.columns:
                    symbols = sorted(
                        data["SYMBOL"].dropna().astype(str).tolist()
                    )

                else:
                    symbols = []

            elif isinstance(data, list):
                symbols = sorted(data)

            else:
                symbols = []

            if symbols:

                pd.DataFrame({"Symbol": symbols}).to_csv(
                    CACHE_FILE,
                    index=False
                )

                print(f"Loaded {len(symbols)} symbols from NSE")

                return symbols

        except Exception as e:

            print(f"NSE Error (Attempt {attempt+1}/3): {e}")

            if attempt < 2:
                time.sleep(3)

    # =========================
    # Load Cache
    # =========================
    if os.path.exists(CACHE_FILE):

        try:

            df = pd.read_csv(CACHE_FILE)

            if "Symbol" in df.columns:

                symbols = (
                    df["Symbol"]
                    .dropna()
                    .astype(str)
                    .tolist()
                )

                print(f"Loaded {len(symbols)} symbols from Cache")

                return symbols

        except Exception as e:

            print("Cache Error:", e)

    print("No F&O symbols available.")

    return []
