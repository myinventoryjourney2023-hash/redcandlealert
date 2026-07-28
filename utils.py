import pandas as pd
import yfinance as yf


def get_ohlc(symbol, period="1d", interval="5m"):

    try:

        df = yf.download(
            symbol + ".NS",
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            multi_level_index=False
        )

        if df is None or df.empty:
            return None

        # Ensure datetime index
        df.index = pd.to_datetime(df.index)

        # Convert to IST if timezone exists
        if df.index.tz is not None:
            df.index = df.index.tz_convert("Asia/Kolkata")

        # Keep only latest trading day's candles
        latest_day = df.index[-1].date()
        df = df[df.index.date == latest_day]

        # Remove zero-volume candles
        if "Volume" in df.columns:
            df = df[df["Volume"] > 0]

        if df.empty:
            return None

        return df

    except Exception as e:

        print(f"{symbol} : {e}")
        return None
