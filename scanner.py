import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from config import (
    TOP_GAINERS,
    TOP_LOSERS,
    MAX_THREADS,
    RETRY_COUNT,
    PERIOD,
    TIMEFRAME,
)

from utils import get_ohlc
from stock_lists import get_stock_list


def scan_stock(symbol):
    """Download one stock and calculate today's % change."""

    for attempt in range(RETRY_COUNT + 1):

        try:

            df = get_ohlc(
                symbol,
                period=PERIOD,
                interval=TIMEFRAME,
            )

            if df is None or df.empty:
                raise Exception("No data")

            day_open = float(df["Open"].iloc[0])
            current_price = float(df["Close"].iloc[-1])

            if day_open == 0:
                raise Exception("Open price is zero")

            change = ((current_price - day_open) / day_open) * 100

            return {
                "symbol": symbol,
                "change": round(change, 2),
                "status": "SUCCESS",
                "data": df
            }

        except Exception:

            if attempt == RETRY_COUNT:
                return {
                    "symbol": symbol,
                    "change": None,
                    "status": "FAILED",
                    "data": None
                }


def scan_market():

    symbols = get_stock_list()

    results = []

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:

        futures = [
            executor.submit(scan_stock, symbol)
            for symbol in symbols
        ]

        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Scanning"
        ):
            results.append(future.result())

    elapsed = time.perf_counter() - start

    return results, elapsed


def prepare_scan_results(results, elapsed):

    success = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] == "FAILED"]

    gainers = sorted(
        success,
        key=lambda x: x["change"],
        reverse=True
    )[:TOP_GAINERS]

    losers = sorted(
        success,
        key=lambda x: x["change"]
    )[:TOP_LOSERS]

    return {
        "gainers": gainers,
        "losers": losers,
        "scan_time": round(elapsed, 2),
        "success": len(success),
        "failed": len(failed),
        "total": len(results),
    }


def show_results(report):

    print("\n========== SCAN SUMMARY ==========")

    print(f"Total Stocks : {report['total']}")
    print(f"Success      : {report['success']}")
    print(f"Failed       : {report['failed']}")
    print(f"Scan Time    : {report['scan_time']} sec")

    print("\n========== TOP GAINERS ==========")

    for stock in report["gainers"]:
        print(f"{stock['symbol']:15} {stock['change']:>7.2f}%")

    print("\n========== TOP LOSERS ==========")

    for stock in report["losers"]:
        print(f"{stock['symbol']:15} {stock['change']:>7.2f}%")
