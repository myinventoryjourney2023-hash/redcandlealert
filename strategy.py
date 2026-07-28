def check_first_two_green(df):
    """
    First candle Green
    Second candle Green
    """

    if len(df) < 4:
        return False

    c1 = df.iloc[0]
    c2 = df.iloc[1]

    first_green = c1["Close"] > c1["Open"]
    second_green = c2["Close"] > c2["Open"]

    return first_green and second_green


def is_lowest_red_volume(df, index):

    current = df.iloc[index]

    # Candle must be RED
    if current["Close"] >= current["Open"]:
        return False

    current_volume = current["Volume"]

    # Ignore zero-volume candles
    volumes = df.iloc[:index + 1]["Volume"]
    volumes = volumes[volumes > 0]

    if len(volumes) == 0:
        return False

    lowest_volume = volumes.min()

    print(
        f"Index={index}  Volume={current_volume}  Lowest={lowest_volume}"
    )

    return current_volume == lowest_volume


def run_long_strategy(df):
    """
    LONG Strategy

    Rules:
    1. First candle Green
    2. Second candle Green
    3. Third candle Ignore
    4. From 4th candle onwards:
       - Red candle
       - Lowest volume till now
    """

    if not check_first_two_green(df):
        return None

    # Start from 4th candle (index = 3)
    for i in range(3, len(df)):

        if is_lowest_red_volume(df, i):

            candle = df.iloc[i]

            return {
                "signal": "LONG",
                "index": i,
                "entry": candle["High"],
                "sl": candle["Low"],
                "volume": candle["Volume"]
            }

    return None
