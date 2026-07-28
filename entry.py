# entry.py

def check_entry_trigger(df, signal):
    """
    Live Entry Trigger

    Only checks the latest completed candle.
    """

    if signal is None:
        return None

    if df is None or len(df) < 2:
        return None

    entry_price = float(signal["entry"])
    signal_index = signal["index"]

    # Latest completed candle
    trigger_index = len(df) - 2

    # Signal candle ke baad hi trigger allow hoga
    if trigger_index <= signal_index:
        return None

    candle = df.iloc[trigger_index]

    if float(candle["High"]) < entry_price:
        return None

    return {
        "triggered": True,
        "entry": round(entry_price, 2),
        "trigger_index": trigger_index,
        "trigger_time": df.index[trigger_index],
        "trigger_high": round(float(candle["High"]), 2),
        "trigger_low": round(float(candle["Low"]), 2),
        "trigger_close": round(float(candle["Close"]), 2),
    }
