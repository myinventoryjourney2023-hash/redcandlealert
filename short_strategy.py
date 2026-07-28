def check_first_two_red(df):

    if len(df) < 4:
        return False

    first = df.iloc[0]
    second = df.iloc[1]

    return (
        first["Close"] < first["Open"] and
        second["Close"] < second["Open"]
    )


def is_lowest_green_volume(df, index):

    current = df.iloc[index]

    # Green candle होना चाहिए
    if current["Close"] <= current["Open"]:
        return False

    current_volume = current["Volume"]

    volumes = df.iloc[:index + 1]["Volume"]
    volumes = volumes[volumes > 0]

    if len(volumes) == 0:
        return False

    lowest_volume = volumes.min()

    return current_volume == lowest_volume


def run_short_strategy(df):

    if not check_first_two_red(df):
        return None

    # 3rd candle ignore
    for i in range(3, len(df)):

        if is_lowest_green_volume(df, i):

            candle = df.iloc[i]

            return {
                "signal": "SHORT",
                "index": i,
                "entry": candle["Low"],
                "sl": candle["High"],
                "volume": candle["Volume"]
            }

    return None
