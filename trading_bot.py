import websocket
import json
import pandas as pd
import pandas_ta as ta
import numpy as np
from binance.client import Client
from binance.enums import *
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from os import system
from time import sleep
import ssl
from urllib import request
import yfinance as yf
import traceback

def read_api_keys(file_path='config.txt'):
    try:
        with open(file_path, 'r') as f:
            api_key = f.readline().strip()
            api_secret = f.readline().strip()
            return api_key, api_secret
    except Exception as e:
        print(f"Error reading API keys from {file_path}: {e}")
        return None, None

class TradingBot:
    def __init__(self, symbol="CKBUSDT", interval=Client.KLINE_INTERVAL_1MINUTE):
        self.api_key, self.api_secret = read_api_keys()
        if not self.api_key or not self.api_secret:
            raise ValueError("API keys could not be loaded from config.txt")
        
        self.client = Client(self.api_key, self.api_secret)
        self.symbol = symbol
        self.interval = interval
        self.in_position = False
        self.data = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'hcl3'])
        
        # Wave Trend parameters
        self.channel_length = 10
        self.average_length = 21
        
        self.check_binance_status()
        
    def check_binance_status(self):
        try:
            response = requests.get("https://api.binance.com/api/v3/ping")
            if response.status_code == 200:
                print("Successfully connected to Binance")
            else:
                print("Binance server is not ready to use. Status code:", response.status_code)
                quit()
        except Exception as e:
            print("Error while accessing Binance. Error code:", e)
            quit()

    def get_account_info(self):
        return {
            'usdt_balance': self.get_usdt_balance(),
            'symbol_balance': self.get_symbol_balance(),
            'maker_commission': self.get_maker_commission(),
            'can_trade': self.client.get_account()['canTrade']
        }

    def get_usdt_balance(self):
        account_info = self.client.get_account()
        for balance in account_info['balances']:
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0

    def get_symbol_balance(self):
        account_info = self.client.get_account()
        symbol_without_usdt = self.symbol.replace('USDT', '')
        for balance in account_info['balances']:
            if balance['asset'] == symbol_without_usdt:
                return float(balance['free'])
        return 0

    def get_maker_commission(self):
        account_info = self.client.get_account()
        return account_info['commissionRates']["maker"]

    def calculate_wave_trend(self, data):
        # Convert data to use integer index to avoid warnings
        df = data.copy()
        df.reset_index(inplace=True, drop=True)
        
        # Calculate HLC3
        df["hcl3"] = (df["high"] + df["close"] + df["low"]) / 3
        
        # Calculate Wave Trend
        esa = ta.ema(df["hcl3"], self.channel_length)
        d = ta.ema(abs(df["hcl3"] - esa), self.channel_length)
        ci = (df["hcl3"] - esa) / (0.015 * d)
        tci = ta.ema(ci, self.average_length)

        wt1 = tci
        wt2 = ta.sma(wt1, 4)

        return wt1, wt2

    def get_signal(self, wt1, wt2):
        """Get trading signal based on Wave Trend crossover
        Returns:
            str: 'buy', 'sell', or 'neutral'
        """
        # Get the last two values
        if len(wt1) < 2 or len(wt2) < 2:
            return "neutral"
            
        # Check for crossover
        prev_wt1, curr_wt1 = wt1[-2:]
        prev_wt2, curr_wt2 = wt2[-2:]
        
        # Bullish crossover (wt1 crosses above wt2)
        if prev_wt1 <= prev_wt2 and curr_wt1 > curr_wt2:
            return "buy"
        # Bearish crossover (wt1 crosses below wt2)
        elif prev_wt1 >= prev_wt2 and curr_wt1 < curr_wt2:
            return "sell"
            
        return "neutral"

    def place_order(self, side, quantity):
        try:
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=quantity
            )
            return order
        except Exception as e:
            print(f'Order Error: {e}')
            return None

    def on_message(self, ws, message):
        system("cls")
        print(f"System date and time: {datetime.now()}")
        print(f"Symbol: {self.symbol}")
        print(f"Position: {'Long' if self.in_position else 'None'}")
        
        msg = json.loads(message)
        if msg['e'] == 'kline':
            candle = msg['k']
            is_candle_closed = candle['x']
            
            if is_candle_closed:
                new_row = {
                    'open': float(candle['o']),
                    'high': float(candle['h']),
                    'low': float(candle['l']),
                    'close': float(candle['c']),
                    'hcl3': 0
                }
                
                self.data.loc[len(self.data)] = new_row
                if len(self.data) > 50:  # Keep only last 50 candles
                    self.data = self.data.iloc[1:]
                
                wt1, wt2 = self.calculate_wave_trend(self.data)
                signal = self.get_signal(wt1, wt2)
                
                print(f"Current price: {candle['c']}")
                print(f"Signal: {signal}")
                
                if signal == "buy" and not self.in_position:
                    usdt_balance = self.get_usdt_balance()
                    quantity = (usdt_balance / float(candle['c'])) * 0.95
                    quantity = int(quantity)
                    
                    if quantity > 0:
                        order = self.place_order(SIDE_BUY, quantity)
                        if order:
                            self.in_position = True
                            print(f"Bought {quantity} {self.symbol}")
                
                elif signal == "sell" and self.in_position:
                    quantity = int(self.get_symbol_balance())
                    if quantity > 0:
                        order = self.place_order(SIDE_SELL, quantity)
                        if order:
                            self.in_position = False
                            print(f"Sold {quantity} {self.symbol}")

    def backtest(self, start_time=None, end_time=None, strategy_type="Special"):
        """
        Run backtest for the specified period
        
        Args:
            start_time (int): Start timestamp in milliseconds
            end_time (int): End timestamp in milliseconds
            strategy_type (str): Strategy type to use for backtesting
            
        Returns:
            list: List of trades executed during backtest
        """
        try:
            print(f"Starting backtest for {self.symbol} from {start_time} to {end_time}")
            
            # Get historical data
            klines = self.client.get_historical_klines(
                self.symbol,
                self.interval,
                start_str=start_time,
                end_str=end_time
            )
            
            if not klines:
                print("No data available for the specified period")
                return []
                
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades_count',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            
            # Convert values to float
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate indicators based on strategy
            if strategy_type == "Special":
                # Wave Trend calculation
                ap = (df['high'] + df['low'] + df['close']) / 3
                esa = ta.ema(ap, length=10)
                d = ta.ema(abs(ap - esa), length=10)
                ci = (ap - esa) / (0.015 * d)
                wt1 = ta.ema(ci, length=21)
                wt2 = ta.sma(wt1, length=4)
                
                df['wt1'] = wt1
                df['wt2'] = wt2
                
            elif strategy_type == "RSI":
                df['rsi'] = ta.rsi(df['close'], length=14)
                
            elif strategy_type == "MACD":
                macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
                df['macd'] = macd['MACD_12_26_9']
                df['signal'] = macd['MACDs_12_26_9']
                df['histogram'] = macd['MACDh_12_26_9']
            
            # Initialize variables
            position = None
            entry_price = 0
            trades = []
            
            # Simulate trading
            for i in range(1, len(df)):
                current_price = df['close'].iloc[i]
                timestamp = df.index[i]
                
                # Get signals based on strategy
                if strategy_type == "Special":
                    wt1 = df['wt1'].iloc[i]
                    wt2 = df['wt2'].iloc[i]
                    wt1_prev = df['wt1'].iloc[i-1]
                    wt2_prev = df['wt2'].iloc[i-1]
                    
                    # Buy signal: WT1 and WT2 cross above -60
                    buy_signal = (wt1_prev <= -60 or wt2_prev <= -60) and (wt1 > -60 and wt2 > -60)
                    
                    # Sell signal: WT1 and WT2 cross below 60
                    sell_signal = (wt1_prev >= 60 or wt2_prev >= 60) and (wt1 < 60 and wt2 < 60)
                    
                elif strategy_type == "RSI":
                    rsi = df['rsi'].iloc[i]
                    rsi_prev = df['rsi'].iloc[i-1]
                    
                    # Buy signal: RSI crosses above 30
                    buy_signal = rsi_prev <= 30 and rsi > 30
                    
                    # Sell signal: RSI crosses below 70
                    sell_signal = rsi_prev >= 70 and rsi < 70
                    
                elif strategy_type == "MACD":
                    macd = df['macd'].iloc[i]
                    signal = df['signal'].iloc[i]
                    macd_prev = df['macd'].iloc[i-1]
                    signal_prev = df['signal'].iloc[i-1]
                    
                    # Buy signal: MACD crosses above Signal
                    buy_signal = macd_prev <= signal_prev and macd > signal
                    
                    # Sell signal: MACD crosses below Signal
                    sell_signal = macd_prev >= signal_prev and macd < signal
                    
                else:
                    continue
                
                # Execute trades
                if position is None and buy_signal:
                    position = "LONG"
                    entry_price = current_price
                    trades.append({
                        'timestamp': int(timestamp.timestamp() * 1000),
                        'type': 'BUY',
                        'price': current_price,
                        'profit': 0
                    })
                    
                elif position == "LONG" and sell_signal:
                    profit = current_price - entry_price
                    trades.append({
                        'timestamp': int(timestamp.timestamp() * 1000),
                        'type': 'SELL',
                        'price': current_price,
                        'profit': profit
                    })
                    position = None
                    entry_price = 0
            
            print(f"Backtest completed with {len(trades)} trades")
            return trades
            
        except Exception as e:
            print(f"Error during backtest: {e}")
            traceback.print_exc()
            return []

    def get_recent_data(self, symbol=None, interval=None, limit=50):
        """Get recent market data for a symbol"""
        symbol = symbol or self.symbol
        interval = interval or self.interval
        
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            df = df[['timestamp', 'open', 'high', 'low', 'close']]
            df = df.astype(float)
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            print(f"Error getting recent data: {e}")
            return pd.DataFrame()

    def start_websocket(self):
        ws = websocket.WebSocketApp(
            f"wss://stream.binance.com:9443/ws/{self.symbol.lower()}@kline_{self.interval}",
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, err: print(err),
            on_close=lambda ws: print("WebSocket Connection Closed"),
            on_open=lambda ws: print("WebSocket Connection Opened")
        )
        
        # Initialize historical data
        historicaldata = self.client.get_klines(
            symbol=self.symbol,
            interval=self.interval,
            limit=50
        )
        
        for candle in historicaldata:
            self.data.loc[len(self.data)] = {
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'hcl3': 0
            }
        
        print(f"Starting WebSocket for {self.symbol}")
        ws.run_forever()

    def backtest_without_api(self, symbol, period="1y", initial_capital=100000):
        """Backtest without using API - for offline testing"""
        try:
            # Get historical data
            data = self.client.get_historical_klines(
                symbol,
                self.interval,
                period
            )
            
            if not data:
                raise ValueError(f"No data available for {symbol}")
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            df = df[['timestamp', 'open', 'high', 'low', 'close']]
            df = df.astype(float)
            df.set_index('timestamp', inplace=True)
            
            wt1, wt2 = self.calculate_wave_trend(df)
            
            position = 0
            position_price = 0
            total_assets = initial_capital
            commission_fee = 0.001  # Default commission fee
            
            trades = []
            
            for i in range(1, len(df)):
                signal = self.get_signal(wt1[:i+1], wt2[:i+1])
                current_time = df.index[i]
                current_price = df['close'].iloc[i]
                
                if signal == "buy" and position == 0:
                    position = 1
                    position_price = current_price
                    total_assets *= (1 - commission_fee)
                    trades.append({
                        'type': 'buy',
                        'price': position_price,
                        'timestamp': current_time,
                        'total_assets': total_assets
                    })
                    
                elif signal == "sell" and position == 1:
                    total_assets *= (1 + (current_price / position_price - 1) * (1 - commission_fee))
                    position = 0
                    trades.append({
                        'type': 'sell',
                        'price': current_price,
                        'timestamp': current_time,
                        'total_assets': total_assets
                    })
            
            if position == 1:
                total_assets *= (1 + (df['close'].iloc[-1] / position_price - 1) * (1 - commission_fee))
            
            return trades, df
            
        except Exception as e:
            print(f"Backtest error: {e}")
            return [], pd.DataFrame()

    def run_backtest(self, start_date, end_date, strategy):
        """Run backtest with selected parameters"""
        try:
            # Get historical data
            data = self.get_historical_data(
                symbol=self.symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if data is None or len(data) == 0:
                print("No data available for backtest")
                return None
            
            # Initialize variables
            trades = []
            position = None
            initial_capital = float(self.config.get('initial_capital', 1000))
            capital = initial_capital
            
            # Run strategy
            signals = self.run_strategy(data, strategy)
            
            # Process signals
            for i in range(len(data)):
                timestamp = data.index[i]
                close = data['close'].iloc[i]
                signal = signals[i] if i < len(signals) else 'NEUTRAL'
                
                # Process buy signal
                if signal == 'BUY' and position is None:
                    position = {
                        'type': 'BUY',
                        'entry_price': close,
                        'timestamp': timestamp,
                        'size': capital / close
                    }
                    trades.append({
                        'timestamp': timestamp,
                        'type': 'BUY',
                        'price': close,
                        'size': position['size'],
                        'value': capital
                    })
                    
                # Process sell signal
                elif signal == 'SELL' and position is not None:
                    # Calculate profit
                    exit_value = position['size'] * close
                    profit = exit_value - (position['size'] * position['entry_price'])
                    capital = exit_value
                    
                    trades.append({
                        'timestamp': timestamp,
                        'type': 'SELL',
                        'price': close,
                        'size': position['size'],
                        'value': capital,
                        'profit': profit
                    })
                    position = None
                
            # Calculate statistics
            if len(trades) > 0:
                final_capital = trades[-1]['value']
                total_return = ((final_capital - initial_capital) / initial_capital) * 100
                win_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
                total_trades = len([t for t in trades if t['type'] == 'SELL'])
                win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
            else:
                final_capital = initial_capital
                total_return = 0
                win_rate = 0
                total_trades = 0
                
            stats = {
                'initial_capital': initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'total_trades': total_trades,
                'win_rate': win_rate
            }
            
            return {
                'data': data,
                'trades': trades,
                'stats': stats
            }
            
        except Exception as e:
            print(f"Backtest error: {e}")
            traceback.print_exc()
            return None

    def get_historical_data(self, symbol=None, start_time=None, end_time=None, interval='1h'):
        """Get historical klines data from Binance"""
        try:
            if symbol is None:
                symbol = self.symbol
                
            # Convert timestamps to string format if they are integers
            if isinstance(start_time, int):
                start_time = str(start_time)
            if isinstance(end_time, int):
                end_time = str(end_time)
                
            # Get klines data
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time,
                limit=1000
            )
            
            if not klines:
                print(f"No historical data available for {symbol}")
                return None
                
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            # Set timestamp as index and sort
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Make sure index is timezone-naive
            df.index = df.index.tz_localize(None)
            
            return df
            
        except Exception as e:
            print(f"Error getting historical data: {e}")
            traceback.print_exc()
            return None

def main():
    # Create trading bot instance
    bot = TradingBot(symbol="CKBUSDT", interval=Client.KLINE_INTERVAL_1MINUTE)
    
    # Run backtest
    print("Running backtest...")
    bot.backtest(period="1y", initial_capital=100000)
    
    # Start live trading
    print("\nStarting live trading...")
    bot.start_websocket()

if __name__ == "__main__":
    main() 