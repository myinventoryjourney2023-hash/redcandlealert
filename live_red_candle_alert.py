import time
from datetime import datetime

from scanner import (
    scan_market,
    prepare_scan_results,
)

from market import get_market_breadth
from long_engine import run_long_engine
from active_monitor import monitor_active_trades


# ==========================
# SETTINGS
# ==========================

SCAN_INTERVAL = 300      # 5 Minutes

MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)


# ==========================
# MARKET STATUS
# ==========================

def market_is_open():

    now = datetime.now()

    # Saturday / Sunday
    if now.weekday() >= 5:
        return False

    current = now.hour * 60 + now.minute

    start = MARKET_OPEN[0] * 60 + MARKET_OPEN[1]
    end = MARKET_CLOSE[0] * 60 + MARKET_CLOSE[1]

    return start <= current <= end


# ==========================
# BOT START
# ==========================

print("=" * 60)
print("LONG BOT STARTED")
print("=" * 60)

while True:

    if not market_is_open():

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            "Market Closed..."
        )

        time.sleep(60)
        continue

    print("\n")
    print("=" * 60)
    print(datetime.now())
    print("Starting Market Scan...")
    print("=" * 60)

    try:

        results, elapsed = scan_market()

        report = prepare_scan_results(
            results,
            elapsed
        )

        breadth = get_market_breadth(results)

        print("\n========== MARKET ==========")
        print(f"Advances : {breadth['advances']}")
        print(f"Declines : {breadth['declines']}")
        print(f"Bullish  : {breadth['bullish']}")

        # ==========================
        # LONG ENGINE
        # ==========================

        run_long_engine(report)

        # ==========================
        # ACTIVE TRADE MONITOR
        # ==========================

        monitor_active_trades(report)

        print("\nCycle Completed Successfully")

    except KeyboardInterrupt:

        print("\nBot Stopped By User")
        break

    except Exception as e:

        print("\n==============================")
        print("BOT ERROR")
        print("==============================")
        print(type(e).__name__)
        print(e)

    print(f"\nSleeping {SCAN_INTERVAL} Seconds...")
    time.sleep(SCAN_INTERVAL)
