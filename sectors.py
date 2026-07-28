SECTOR_MAP = {

    # IT
    "TCS": "IT",
    "INFY": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "LTIM": "IT",
    "PERSISTENT": "IT",
    "MPHASIS": "IT",
    "COFORGE": "IT",
    "OFSS": "IT",

    # BANK
    "HDFCBANK": "BANK",
    "ICICIBANK": "BANK",
    "SBIN": "BANK",
    "AXISBANK": "BANK",
    "KOTAKBANK": "BANK",
    "INDUSINDBK": "BANK",
    "FEDERALBNK": "BANK",
    "PNB": "BANK",
    "BANKBARODA": "BANK",
    "IDFCFIRSTB": "BANK",

    # FINANCIAL SERVICES
    "BAJFINANCE": "FINANCIAL",
    "BAJAJFINSV": "FINANCIAL",
    "CHOLAFIN": "FINANCIAL",
    "SHRIRAMFIN": "FINANCIAL",
    "LICHSGFIN": "FINANCIAL",
    "MUTHOOTFIN": "FINANCIAL"
}


def get_stock_sector(symbol):
    return SECTOR_MAP.get(symbol, "UNKNOWN")


def get_stocks_by_sector(sector):

    stocks = []

    for symbol, stock_sector in SECTOR_MAP.items():

        if stock_sector == sector:
            stocks.append(symbol)

    return stocks


def get_top_sector(gainers):

    sector_totals = {}
    sector_counts = {}

    for stock in gainers:

        symbol = stock["symbol"]
        change = stock["change"]

        sector = get_stock_sector(symbol)

        if sector == "UNKNOWN":
            continue

        if sector not in sector_totals:
            sector_totals[sector] = 0
            sector_counts[sector] = 0

        sector_totals[sector] += change
        sector_counts[sector] += 1

    best_sector = None
    best_average = -999

    for sector in sector_totals:

        average = sector_totals[sector] / sector_counts[sector]

        if average > best_average:
            best_average = average
            best_sector = sector

    return best_sector
