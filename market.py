def get_market_breadth(results):

    advances = 0
    declines = 0

    for stock in results:

        if stock["status"] != "SUCCESS":
            continue

        if stock["change"] > 0:
            advances += 1

        elif stock["change"] < 0:
            declines += 1

    return {
        "advances": advances,
        "declines": declines,
        "bullish": advances > declines
    }
