def custom_strategy(data):
    # data is a pandas DataFrame with columns: open, high, low, close, volume
    # Available indicators: RSI, SMA, EMA, MACD, etc. (using pandas_ta)
    # Example:
    rsi = data.ta.rsi(close='close', length=14).iloc[-1]
    sma20 = data.ta.sma(close='close', length=20).iloc[-1]

    if rsi < 30 and data['close'].iloc[-1] > sma20:
        return 'BUY'
    elif rsi > 70 and data['close'].iloc[-1] < sma20:
        return 'SELL'

    return 'NEUTRAL'

