from long_engine import run_long_engine
from market import get_market_breadth
from sectors import get_top_sector
from scanner import (
    scan_market,
    prepare_scan_results,
    show_results,
)

results, elapsed = scan_market()

report = prepare_scan_results(results, elapsed)
breadth = get_market_breadth(results)

print("\n========== MARKET ==========")
print(f"Advances : {breadth['advances']}")
print(f"Declines : {breadth['declines']}")
print(f"Bullish  : {breadth['bullish']}")

show_results(report)

top_sector = get_top_sector(report["gainers"])

print("\n========== TOP SECTOR ==========")
print(top_sector)

print("\n========== LONG STRATEGY ==========")

run_long_engine(report)
