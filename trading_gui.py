import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QComboBox, 
                           QTableWidget, QTableWidgetItem, QTabWidget, 
                           QLineEdit, QGridLayout, QProgressBar, QMessageBox,
                           QSplitter, QCompleter, QFrame, QTextEdit, QDateTimeEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QStringListModel, QDateTime
from PyQt5.QtGui import QPalette, QColor, QFont
import pandas as pd
from trading_bot import TradingBot
from datetime import datetime
import threading
from chart_widget import TradingChart
import pandas_ta as ta
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

class CoinInfoWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QGridLayout(self)
        layout.setSpacing(10)
        
        # Coin search with icon
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search coin (e.g., BTC, ETH)")
        self.search_input.setMinimumWidth(200)
        search_layout.addWidget(self.search_input)
        
        # Info layout
        info_layout = QGridLayout()
        info_layout.setSpacing(15)
        
        # Create styled labels
        self.price_label = QLabel("Price: -")
        self.volume_label = QLabel("24h Volume: -")
        self.change_label = QLabel("24h Change: -")
        self.high_label = QLabel("24h High: -")
        self.low_label = QLabel("24h Low: -")
        
        # Add icons to labels
        self.price_label.setText("💰 Price: -")
        self.volume_label.setText("📊 24h Volume: -")
        self.change_label.setText("📈 24h Change: -")
        self.high_label.setText("⬆️ 24h High: -")
        self.low_label.setText("⬇️ 24h Low: -")
        
        # Style labels
        for label in [self.price_label, self.volume_label, self.change_label, 
                     self.high_label, self.low_label]:
            font = label.font()
            font.setPointSize(10)
            label.setFont(font)
            label.setMinimumWidth(200)
        
        # Add to layout with proper spacing
        layout.addLayout(search_layout, 0, 0, 1, 2)
        layout.addWidget(self.price_label, 1, 0)
        layout.addWidget(self.volume_label, 1, 1)
        layout.addWidget(self.change_label, 2, 0)
        layout.addWidget(self.high_label, 2, 1)
        layout.addWidget(self.low_label, 3, 0)
        
        # Add some padding
        layout.setContentsMargins(15, 15, 15, 15)
        
    def update_info(self, info):
        self.price_label.setText(f"💰 Price: {info['price']:.8f} USDT")
        self.volume_label.setText(f"📊 24h Volume: {info['volume']:,.2f} USDT")
        
        change = info['price_change']
        icon = "📈" if change >= 0 else "📉"
        color = "#4caf50" if change >= 0 else "#f44336"
        self.change_label.setText(f"{icon} 24h Change: <span style='color: {color}'>{change:+.2f}%</span>")
        
        self.high_label.setText(f"⬆️ 24h High: {info['high']:.8f} USDT")
        self.low_label.setText(f"⬇️ 24h Low: {info['low']:.8f} USDT")

class MarketOverviewWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 10px;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: white;
                gridline-color: #424242;
                border: none;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #424242;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: white;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #007acc;
                font-weight: bold;
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Market overview table
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(6)
        self.market_table.setHorizontalHeaderLabels([
            "Symbol 💱", "Price 💰", "24h Change 📊", 
            "Volume 📈", "Market Cap 💎", "Signals 🎯"
        ])
        
        # Style
        self.market_table.setAlternatingRowColors(True)
        self.market_table.horizontalHeader().setStretchLastSection(True)
        self.market_table.verticalHeader().setVisible(False)
        self.market_table.setShowGrid(False)
        self.market_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.market_table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Set column widths
        self.market_table.setColumnWidth(0, 120)  # Symbol
        self.market_table.setColumnWidth(1, 150)  # Price
        self.market_table.setColumnWidth(2, 120)  # Change
        self.market_table.setColumnWidth(3, 150)  # Volume
        self.market_table.setColumnWidth(4, 150)  # Market Cap
        
        layout.addWidget(self.market_table)
        
    def update_market_data(self, data):
        self.market_table.setRowCount(len(data))
        for i, row in enumerate(data):
            # Symbol with icon
            symbol_item = QTableWidgetItem(f"🔸 {row['symbol']}")
            self.market_table.setItem(i, 0, symbol_item)
            
            # Price with formatting
            price_item = QTableWidgetItem(f"{row['price']:.8f}")
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.market_table.setItem(i, 1, price_item)
            
            # Change with color
            change_text = f"{row['change']:+.2f}%"
            change_item = QTableWidgetItem(change_text)
            change_item.setForeground(QColor("#4caf50" if row['change'] >= 0 else "#f44336"))
            change_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.market_table.setItem(i, 2, change_item)
            
            # Volume with formatting
            volume_item = QTableWidgetItem(f"{row['volume']:,.2f}")
            volume_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.market_table.setItem(i, 3, volume_item)
            
            # Market cap with formatting
            market_cap_item = QTableWidgetItem(f"{row['market_cap']:,.2f}")
            market_cap_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.market_table.setItem(i, 4, market_cap_item)
            
            # Signal with icon
            signal_icon = "🔵" if row['signal'] == "neutral" else "🟢" if row['signal'] == "buy" else "🔴"
            signal_item = QTableWidgetItem(f"{signal_icon} {row['signal'].upper()}")
            self.market_table.setItem(i, 5, signal_item)

class ScannerThread(QThread):
    signal_update = pyqtSignal(list)
    
    def __init__(self, min_volume):
        super().__init__()
        self.bot = TradingBot()  # Create a single bot instance
        self.min_volume = min_volume
        self.is_running = True
        
    def run(self):
        while self.is_running:
            try:
                # Get all USDT pairs
                tickers = self.bot.client.get_ticker()
                signals = []
                
                for ticker in tickers:
                    if ticker['symbol'].endswith('USDT'):
                        volume_usdt = float(ticker['volume']) * float(ticker['lastPrice'])
                        
                        if volume_usdt >= self.min_volume:
                            try:
                                # Get recent data and calculate signal
                                data = self.bot.get_recent_data(symbol=ticker['symbol'], limit=50)
                                wt1, wt2 = self.bot.calculate_wave_trend(data)
                                signal = self.bot.get_signal(wt1, wt2)
                                
                                if signal != "neutral":  # Only add if there's a signal
                                    signals.append({
                                        'symbol': ticker['symbol'],
                                        'signal': signal,
                                        'price': float(ticker['lastPrice']),
                                        'volume': volume_usdt,
                                        'timestamp': datetime.now()
                                    })
                            except:
                                continue
                
                # Sort by volume
                signals.sort(key=lambda x: x['volume'], reverse=True)
                self.signal_update.emit(signals)
                
            except Exception as e:
                print(f"Scanner error: {e}")
                
            # Sleep for 1 minute
            for _ in range(60):  # Check is_running every second
                if not self.is_running:
                    break
                self.sleep(1)
            
    def stop(self):
        self.is_running = False

class TradingThread(QThread):
    signal_update = pyqtSignal(dict)
    signal_chart_update = pyqtSignal(object, object, object)  # data, wt1, wt2
    
    def __init__(self, bot, symbol, interval):
        super().__init__()
        self.bot = bot
        self.bot.symbol = symbol
        self.symbol = symbol
        self.interval = interval
        self.is_running = True
        
    def run(self):
        while self.is_running:
            try:
                # Get account info
                info = {
                    'balance': self.bot.get_usdt_balance(),
                    'position': self.bot.in_position,
                    'symbol_balance': self.bot.get_symbol_balance(),
                    'timestamp': datetime.now()
                }
                self.signal_update.emit(info)
                
                # Get latest market data
                data = self.bot.get_recent_data(symbol=self.symbol, interval=self.interval, limit=100)
                wt1, wt2 = self.bot.calculate_wave_trend(data)
                self.signal_chart_update.emit(data, wt1, wt2)
                
            except Exception as e:
                print(f"Trading thread error: {e}")
            
            # Update interval based on selected timeframe
            sleep_time = {
                "1m": 1,
                "5m": 5,
                "15m": 15,
                "1h": 60,
                "4h": 240,
                "1d": 1440
            }.get(self.interval, 1)
            
            # Sleep for the appropriate interval, checking is_running every second
            for _ in range(sleep_time):
                if not self.is_running:
                    break
                self.sleep(1)
    
    def stop(self):
        self.is_running = False

class TradingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HolyStar Trading Bot")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #424242;
                background: #1e1e1e;
            }
            QTabWidget::tab-bar {
                left: 5px;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #ffffff;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #3d3d3d;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover {
                background: #3d3d3d;
            }
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0098ff;
            }
            QPushButton:pressed {
                background-color: #005c99;
            }
            QPushButton:disabled {
                background-color: #4d4d4d;
                color: #9d9d9d;
            }
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #424242;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #007acc;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: white;
                gridline-color: #424242;
                border: 1px solid #424242;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #007acc;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: white;
                padding: 5px;
                border: 1px solid #424242;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #424242;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLabel {
                color: white;
            }
        """)
        
        try:
            print("Initializing Trading Bot...")
            # Create single TradingBot instance
            self.trading_bot = TradingBot()
            self.current_symbol = ""  # Track current symbol
            self.current_interval = "1m"  # Track current interval
            
            # Create main widget and layout
            main_widget = QWidget()
            self.setCentralWidget(main_widget)
            layout = QVBoxLayout(main_widget)
            
            # Create tab widget
            tabs = QTabWidget()
            layout.addWidget(tabs)
            
            # Create tabs
            trading_tab = QWidget()
            backtest_tab = QWidget()
            market_tab = QWidget()
            strategy_tab = QWidget()  
            
            # Setup all tabs
            self.setup_trading_tab(trading_tab)
            self.setup_market_tab(market_tab)
            self.setup_backtest_tab(backtest_tab)
            self.setup_strategy_tab(strategy_tab) 
            
            # Add tabs
            tabs.addTab(trading_tab, "Trading")
            tabs.addTab(market_tab, "Market Overview")
            tabs.addTab(backtest_tab, "Backtest")
            tabs.addTab(strategy_tab, "Strategy Editor") 
            
            # Initialize threads
            self.trading_thread = None
            self.market_thread = None
            
            # Load custom strategies
            self.load_custom_strategies()
            
            # Set dark theme
            self.set_dark_theme()
            
            # Initialize coin list and completer
            self.initialize_coin_list()
            
            print("Starting market updates...")
            # Start market updates
            self.start_market_updates()
            
            print("GUI initialization completed")
            
        except Exception as e:
            print(f"Failed to initialize application: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to initialize application: {str(e)}")
            
    def start_market_updates(self):
        """Start market data updates in a separate thread"""
        try:
            print("Creating market update thread...")
            if hasattr(self, 'market_thread') and self.market_thread and self.market_thread.isRunning():
                print("Stopping existing market thread...")
                self.market_thread.stop()
                self.market_thread.wait()
            
            self.market_thread = MarketUpdateThread(self.trading_bot)
            
            # Connect signals before starting the thread
            print("Connecting market update signals...")
            self.market_thread.signal_update.connect(self.update_market_table)
            self.market_thread.signal_stats.connect(self.update_market_stats)
            
            print("Starting market thread...")
            self.market_thread.start()
            
            # Wait a bit to ensure the thread has started
            QThread.msleep(100)
            
            if self.market_thread.isRunning():
                print("Market update thread started successfully")
            else:
                print("Market thread failed to start")
                
        except Exception as e:
            print(f"Failed to start market updates: {e}")
            traceback.print_exc()
            QMessageBox.warning(self, "Warning", f"Failed to start market updates: {str(e)}")
            
    def update_market_table(self, market_data):
        """Update market table with new data"""
        try:
            print(f"Updating market table with {len(market_data)} coins")
            self.market_table.setRowCount(len(market_data))
            for i, data in enumerate(market_data):
                # Symbol
                self.market_table.setItem(i, 0, QTableWidgetItem(f"🔸 {data['symbol']}"))
                
                # Price
                self.market_table.setItem(i, 1, QTableWidgetItem(f"{data['price']:.8f}"))
                
                # Change
                change_item = QTableWidgetItem(f"{data['change']:+.2f}%")
                change_item.setForeground(QColor("green" if data['change'] >= 0 else "red"))
                self.market_table.setItem(i, 2, change_item)
                
                # High & Low
                self.market_table.setItem(i, 3, QTableWidgetItem(f"{data['high']:.8f}"))
                self.market_table.setItem(i, 4, QTableWidgetItem(f"{data['low']:.8f}"))
                
                # Volume
                self.market_table.setItem(i, 5, QTableWidgetItem(f"{data['volume']:,.2f}"))
                
                # Market Cap
                market_cap = data['price'] * data['volume']
                self.market_table.setItem(i, 6, QTableWidgetItem(f"{market_cap:,.2f}"))
                
                # Signal
                signal_item = QTableWidgetItem(f"🟢 {data['signal'].upper()}")
                if data['signal'] == "BUY":
                    signal_item.setForeground(QColor("green"))
                elif data['signal'] == "SELL":
                    signal_item.setForeground(QColor("red"))
                self.market_table.setItem(i, 7, signal_item)
                
                # RSI
                if 'rsi' in data:
                    rsi_item = QTableWidgetItem(f"{data['rsi']:.1f}")
                    if data['rsi'] >= 70:
                        rsi_item.setForeground(QColor("red"))
                    elif data['rsi'] <= 30:
                        rsi_item.setForeground(QColor("green"))
                    self.market_table.setItem(i, 8, rsi_item)
                
                # Trend
                if 'trend' in data:
                    trend_item = QTableWidgetItem(data['trend'])
                    if data['trend'] == "BULLISH":
                        trend_item.setForeground(QColor("green"))
                    elif data['trend'] == "BEARISH":
                        trend_item.setForeground(QColor("red"))
                    self.market_table.setItem(i, 9, trend_item)
            
            print("Market table updated successfully")
            
            # Reapply filters if they exist
            if (self.volume_filter.text() or 
                self.change_filter.text() or 
                self.cap_filter.text()):
                self.apply_market_filters()
                
        except Exception as e:
            print(f"Market table update error: {e}")
            
    def update_market_stats(self, stats):
        """Update market statistics"""
        try:
            print("Updating market stats...")
            self.total_market_cap.setText(f"Total Market Cap: ${stats['total_market_cap']:,.2f}")
            self.total_volume.setText(f"24h Volume: ${stats['total_volume']:,.2f}")
            
            if stats['btc_price'] > 0:
                btc_dominance = (stats['btc_market_cap'] / stats['total_market_cap']) * 100
                eth_dominance = (stats['eth_market_cap'] / stats['total_market_cap']) * 100
                self.btc_dominance.setText(f"BTC Dominance: {btc_dominance:.2f}%")
                self.eth_dominance.setText(f"ETH Dominance: {eth_dominance:.2f}%")
                print(f"BTC Dominance: {btc_dominance:.2f}%, ETH Dominance: {eth_dominance:.2f}%")
            
            # Update top gainers/losers with more detail
            price_changes = stats['price_changes']
            price_changes.sort(key=lambda x: x[1], reverse=True)
            
            gainers = [f"{sym}: <font color='green'>+{chg:.2f}%</font>" for sym, chg in price_changes[:5]]
            losers = [f"{sym}: <font color='red'>{chg:.2f}%</font>" for sym, chg in price_changes[-5:]]
            volumes = sorted([(sym, vol) for sym, vol in stats['volumes'].items()], 
                           key=lambda x: x[1], reverse=True)[:5]
            
            self.top_gainers.setText("Top Gainers: " + " | ".join(gainers))
            self.top_losers.setText("Top Losers: " + " | ".join(losers))
            self.top_volume.setText("Top Volume: " + " | ".join([f"{sym}: ${vol:,.0f}" for sym, vol in volumes]))
            
            # Calculate and update market sentiment
            gainers_count = sum(1 for _, chg in price_changes if chg > 0)
            total_coins = len(price_changes)
            sentiment_ratio = gainers_count / total_coins if total_coins > 0 else 0
            
            if sentiment_ratio >= 0.7:
                sentiment = "<font color='green'>Very Bullish</font>"
            elif sentiment_ratio >= 0.6:
                sentiment = "<font color='lightgreen'>Bullish</font>"
            elif sentiment_ratio >= 0.4:
                sentiment = "<font color='yellow'>Neutral</font>"
            elif sentiment_ratio >= 0.3:
                sentiment = "<font color='orange'>Bearish</font>"
            else:
                sentiment = "<font color='red'>Very Bearish</font>"
                
            self.market_sentiment.setText(f"Market Sentiment: {sentiment} ({gainers_count}/{total_coins} coins rising)")
            print("Market stats updated successfully")
            
        except Exception as e:
            print(f"Market stats update error: {e}")
            traceback.print_exc()

    def initialize_coin_list(self):
        try:
            # Use existing trading bot instance
            exchange_info = self.trading_bot.client.get_exchange_info()
            self.coin_list = [symbol['symbol'] for symbol in exchange_info['symbols'] 
                            if symbol['quoteAsset'] == 'USDT']
            
            # Create completer
            completer = QCompleter(self.coin_list)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setFilterMode(Qt.MatchContains)
            
            # Add completer to search input
            self.coin_info_widget.search_input.setCompleter(completer)
            
            # Update backtest symbol combo
            self.backtest_symbol_combo.addItems(self.coin_list)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to initialize coin list: {str(e)}")
        
    def set_dark_theme(self):
        app = QApplication.instance()
        palette = QPalette()
        
        # Ana renkler
        background_color = QColor("#1e1e1e")  # Koyu arka plan
        text_color = QColor("#ffffff")        # Beyaz metin
        accent_color = QColor("#0d47a1")      # Mavi vurgu
        secondary_bg = QColor("#2d2d2d")      # İkincil arka plan
        button_color = QColor("#424242")      # Buton rengi
        
        # Temel renkler
        palette.setColor(QPalette.Window, background_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, secondary_bg)
        palette.setColor(QPalette.AlternateBase, background_color)
        palette.setColor(QPalette.ToolTipBase, accent_color)
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, button_color)
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, accent_color)
        palette.setColor(QPalette.Highlight, accent_color)
        palette.setColor(QPalette.HighlightedText, text_color)
        
        app.setPalette(palette)
        
        # Global stil tanımlamaları
        app.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #424242;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #424242;
                color: #ffffff;
                padding: 8px 20px;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0d47a1;
            }
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #424242;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #424242;
                color: #ffffff;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #2d2d2d;
                color: #666666;
            }
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #424242;
                padding: 5px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #0d47a1;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #424242;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QTableWidget {
                background-color: #2d2d2d;
                color: #ffffff;
                gridline-color: #424242;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #0d47a1;
            }
            QHeaderView::section {
                background-color: #424242;
                color: #ffffff;
                padding: 5px;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #424242;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4a4a4a;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 12px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background-color: #424242;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
            }
        """)
        
    def setup_trading_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Top section with coin info and controls
        top_section = QHBoxLayout()
        
        # Coin info widget
        self.coin_info_widget = CoinInfoWidget()  # Create instance here
        top_section.addWidget(self.coin_info_widget)
        
        # Trading controls
        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        controls_layout = QGridLayout(controls_frame)
        
        # Add interval selection
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Interval:"))
        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"])
        self.interval_combo.setCurrentText("1h")
        self.interval_combo.currentTextChanged.connect(self.on_interval_changed)
        
        # Create date range selection
        self.start_date = QDateTimeEdit()
        self.start_date.setDateTime(QDateTime.currentDateTime().addYears(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("""
            QDateTimeEdit {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #424242;
                padding: 5px;
                border-radius: 3px;
            }
            QDateTimeEdit::drop-down {
                border: none;
                width: 20px;
            }
            QDateTimeEdit::down-arrow {
                image: none;
                border: none;
                background: #424242;
                width: 12px;
                height: 12px;
            }
            QCalendarWidget {
                background-color: #2d2d2d;
                color: white;
            }
            QCalendarWidget QToolButton {
                color: white;
                background-color: #424242;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QCalendarWidget QMenu {
                background-color: #2d2d2d;
                color: white;
            }
            QCalendarWidget QSpinBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #424242;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        
        self.end_date = QDateTimeEdit()
        self.end_date.setDateTime(QDateTime.currentDateTime())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet(self.start_date.styleSheet())  # Aynı stili kullan

        # Add to layout
        interval_layout.addWidget(self.interval_combo)
        interval_layout.addWidget(QLabel("Start Date:"))
        interval_layout.addWidget(self.start_date)
        interval_layout.addWidget(QLabel("End Date:"))
        interval_layout.addWidget(self.end_date)
        interval_layout.addStretch()
        
        controls_layout.addLayout(interval_layout, 0, 0, 1, 2)
        
        # Strategy selection
        strategy_label = QLabel("Strategy:")
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["Special", "RSI", "MACD", "Custom"])
        self.strategy_combo.currentTextChanged.connect(self.on_strategy_changed)
        controls_layout.addWidget(strategy_label, 1, 0)
        controls_layout.addWidget(self.strategy_combo, 1, 1)
        
        # Strategy parameters frame
        self.strategy_params_frame = QFrame()
        strategy_params_layout = QGridLayout(self.strategy_params_frame)
        
        # Add strategy parameters
        # RSI parameters
        self.rsi_length_label = QLabel("RSI Length:")
        self.rsi_length_input = QLineEdit("14")
        self.rsi_overbought_label = QLabel("Overbought:")
        self.rsi_overbought_input = QLineEdit("70")
        self.rsi_oversold_label = QLabel("Oversold:")
        self.rsi_oversold_input = QLineEdit("30")
        
        # MACD parameters
        self.macd_fast_label = QLabel("MACD Fast:")
        self.macd_fast_input = QLineEdit("12")
        self.macd_slow_label = QLabel("MACD Slow:")
        self.macd_slow_input = QLineEdit("26")
        self.macd_signal_label = QLabel("MACD Signal:")
        self.macd_signal_input = QLineEdit("9")
        
        # Add parameters to layout
        strategy_params_layout.addWidget(self.rsi_length_label, 0, 0)
        strategy_params_layout.addWidget(self.rsi_length_input, 0, 1)
        strategy_params_layout.addWidget(self.rsi_overbought_label, 1, 0)
        strategy_params_layout.addWidget(self.rsi_overbought_input, 1, 1)
        strategy_params_layout.addWidget(self.rsi_oversold_label, 2, 0)
        strategy_params_layout.addWidget(self.rsi_oversold_input, 2, 1)
        
        strategy_params_layout.addWidget(self.macd_fast_label, 0, 2)
        strategy_params_layout.addWidget(self.macd_fast_input, 0, 3)
        strategy_params_layout.addWidget(self.macd_slow_label, 1, 2)
        strategy_params_layout.addWidget(self.macd_slow_input, 1, 3)
        strategy_params_layout.addWidget(self.macd_signal_label, 2, 2)
        strategy_params_layout.addWidget(self.macd_signal_input, 2, 3)
        
        controls_layout.addWidget(self.strategy_params_frame, 2, 0, 1, 2)
        
        # Custom strategy frame
        self.custom_strategy_frame = QFrame()
        custom_strategy_layout = QVBoxLayout(self.custom_strategy_frame)
        
        custom_strategy_label = QLabel("Custom Strategy Code:")
        self.custom_strategy_editor = QTextEdit()
        self.custom_strategy_editor.setPlaceholderText(
            "# Define your strategy here\n"
            "def custom_strategy(data):\n"
            "    # Return 'BUY', 'SELL', or 'NEUTRAL'\n"
            "    return 'NEUTRAL'"
        )
        
        custom_strategy_layout.addWidget(custom_strategy_label)
        custom_strategy_layout.addWidget(self.custom_strategy_editor)
        controls_layout.addWidget(self.custom_strategy_frame, 3, 0, 1, 2)
        self.custom_strategy_frame.hide()
        
        # Start/Stop buttons
        self.start_button = QPushButton("Start Trading")
        self.start_button.clicked.connect(self.start_trading)
        self.stop_button = QPushButton("Stop Trading")
        self.stop_button.clicked.connect(self.stop_trading)
        self.stop_button.setEnabled(False)
        
        controls_layout.addWidget(self.start_button, 4, 0)
        controls_layout.addWidget(self.stop_button, 4, 1)
        
        # Status labels
        self.balance_label = QLabel("USDT Balance: 0")
        self.position_label = QLabel("Position: None")
        self.last_update_label = QLabel("Last Update: Never")
        self.strategy_status_label = QLabel("Active Strategy: Special")
        
        controls_layout.addWidget(self.balance_label, 5, 0, 1, 2)
        controls_layout.addWidget(self.position_label, 6, 0, 1, 2)
        controls_layout.addWidget(self.last_update_label, 7, 0, 1, 2)
        controls_layout.addWidget(self.strategy_status_label, 8, 0, 1, 2)
        
        # Add trading chart
        self.chart_widget = TradingChart()
        
        # Add everything to main layout
        layout.addLayout(top_section)
        layout.addWidget(self.chart_widget)
        layout.addWidget(controls_frame)
        
        # Connect coin search to update trading info
        self.coin_info_widget.search_input.textChanged.connect(self.on_coin_search_changed)
        
        # Hide all parameters initially
        self.hide_all_strategy_params()

    def hide_all_strategy_params(self):
        """Hide all strategy parameter inputs"""
        # RSI parameters
        self.rsi_length_label.hide()
        self.rsi_length_input.hide()
        self.rsi_overbought_label.hide()
        self.rsi_overbought_input.hide()
        self.rsi_oversold_label.hide()
        self.rsi_oversold_input.hide()
        
        # MACD parameters
        self.macd_fast_label.hide()
        self.macd_fast_input.hide()
        self.macd_slow_label.hide()
        self.macd_slow_input.hide()
        self.macd_signal_label.hide()
        self.macd_signal_input.hide()
        
    def show_rsi_params(self):
        """Show RSI strategy parameters"""
        self.hide_all_strategy_params()
        self.rsi_length_label.show()
        self.rsi_length_input.show()
        self.rsi_overbought_label.show()
        self.rsi_overbought_input.show()
        self.rsi_oversold_label.show()
        self.rsi_oversold_input.show()
        
    def show_macd_params(self):
        """Show MACD strategy parameters"""
        self.hide_all_strategy_params()
        self.macd_fast_label.show()
        self.macd_fast_input.show()
        self.macd_slow_label.show()
        self.macd_slow_input.show()
        self.macd_signal_label.show()
        self.macd_signal_input.show()
        
    def on_strategy_changed(self, strategy):
        """Handle strategy selection changes"""
        self.strategy_status_label.setText(f"Active Strategy: {strategy}")
        
        # Hide custom strategy editor by default
        self.custom_strategy_frame.hide()
        
        if strategy == "RSI":
            self.show_rsi_params()
        elif strategy == "MACD":
            self.show_macd_params()
        elif strategy == "Custom":
            self.hide_all_strategy_params()
            self.custom_strategy_frame.show()
        else:  # Special
            self.hide_all_strategy_params()
            
    def save_custom_strategy(self):
        """Save and validate custom strategy code"""
        try:
            code = self.custom_strategy_editor.toPlainText()
            # Basic validation
            if "def custom_strategy" not in code:
                raise ValueError("Strategy must contain 'custom_strategy' function")
                
            # Save to file
            with open("custom_strategy.py", "w") as f:
                f.write(code)
                
            QMessageBox.information(self, "Success", "Custom strategy saved successfully!")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save strategy: {str(e)}")

    def on_interval_changed(self, interval):
        """Handle interval changes"""
        self.current_interval = interval
        if self.trading_thread and self.trading_thread.isRunning():
            # Restart trading thread with new interval
            self.stop_trading()
            self.start_trading()

    def start_trading(self):
        symbol = self.coin_info_widget.search_input.text().upper()
        if not symbol:
            QMessageBox.warning(self, "Error", "Please select a trading pair first")
            return
            
        self.current_symbol = symbol
        interval = self.interval_combo.currentText()
        self.current_interval = interval
        
        # Create trading thread with existing bot instance
        self.trading_thread = TradingThread(self.trading_bot, symbol, interval)
        self.trading_thread.signal_update.connect(self.update_trading_info)
        self.trading_thread.signal_chart_update.connect(self.update_chart)
        self.trading_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Initial chart update
        try:
            data = self.trading_bot.get_recent_data(symbol=symbol, interval=interval, limit=100)
            wt1, wt2 = self.trading_bot.calculate_wave_trend(data)
            self.chart_widget.update_chart(data, wt1, wt2)
        except Exception as e:
            print(f"Initial chart update error: {e}")

    def stop_trading(self):
        if self.trading_thread:
            self.trading_thread.stop()
            self.trading_thread.wait()
            self.trading_thread = None
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def update_trading_info(self, info):
        self.balance_label.setText(f"USDT Balance: {info['balance']:.2f}")
        self.position_label.setText(f"Position: {'Long' if info['position'] else 'None'}")
        self.last_update_label.setText(f"Last Update: {info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        
    def update_chart(self, data, wt1, wt2):
        try:
            self.chart_widget.update_chart(data, wt1, wt2)
        except Exception as e:
            print(f"Chart update error: {e}")
        
    def setup_backtest_tab(self, tab):
        layout = QGridLayout(tab)
        
        # Sol panel - Kontroller
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        left_layout = QVBoxLayout(left_panel)
        
        # Sembol ve strateji seçimi grubu
        selection_group = QFrame()
        selection_layout = QGridLayout(selection_group)
        
        # Sembol seçimi
        symbol_label = QLabel("Symbol:")
        symbol_label.setStyleSheet("font-weight: bold;")
        self.backtest_symbol_combo = QComboBox()
        self.backtest_symbol_combo.setMinimumWidth(200)
        
        # Interval seçimi
        interval_label = QLabel("Interval:")
        interval_label.setStyleSheet("font-weight: bold;")
        self.backtest_interval_combo = QComboBox()
        self.backtest_interval_combo.addItems(["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"])
        self.backtest_interval_combo.setCurrentText("1h")
        
        # Strateji seçimi
        strategy_label = QLabel("Strategy:")
        strategy_label.setStyleSheet("font-weight: bold;")
        self.backtest_strategy_combo = QComboBox()
        self.backtest_strategy_combo.addItems(["Special", "RSI", "MACD", "Custom"])
        self.backtest_strategy_combo.currentTextChanged.connect(self.on_backtest_strategy_changed)
        
        selection_layout.addWidget(symbol_label, 0, 0)
        selection_layout.addWidget(self.backtest_symbol_combo, 0, 1)
        selection_layout.addWidget(interval_label, 1, 0)
        selection_layout.addWidget(self.backtest_interval_combo, 1, 1)
        selection_layout.addWidget(strategy_label, 2, 0)
        selection_layout.addWidget(self.backtest_strategy_combo, 2, 1)
        
        left_layout.addWidget(selection_group)
        
        # Tarih seçimi grubu
        date_group = QFrame()
        date_group.setStyleSheet("""
            QFrame {
                border: 1px solid #424242;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton {
                min-width: 100px;
                padding: 5px 10px;
                margin: 2px;
            }
            QDateTimeEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 5px;
                min-width: 200px;
            }
            QDateTimeEdit::drop-down {
                border: none;
                width: 20px;
            }
            QDateTimeEdit::down-arrow {
                image: none;
                width: 12px;
                height: 12px;
                background: #424242;
            }
            QCalendarWidget {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QCalendarWidget QToolButton {
                color: #ffffff;
                background-color: #424242;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QCalendarWidget QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QCalendarWidget QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #424242;
                border-radius: 3px;
                padding: 3px;
            }
        """)
        date_layout = QVBoxLayout(date_group)
        
        # Tarih başlığı
        date_title = QLabel("Date Range")
        date_title.setStyleSheet("font-size: 12pt; font-weight: bold; margin-bottom: 10px;")
        date_layout.addWidget(date_title)
        
        # Hızlı tarih seçimi butonları
        quick_date_frame = QFrame()
        quick_date_layout = QGridLayout(quick_date_frame)
        quick_date_layout.setSpacing(5)
        
        self.last_week_btn = QPushButton("Last Week")
        self.last_month_btn = QPushButton("Last Month")
        self.last_3months_btn = QPushButton("Last 3 Months")
        self.last_6months_btn = QPushButton("Last 6 Months")
        self.last_year_btn = QPushButton("Last Year")
        self.max_range_btn = QPushButton("Max Range")
        
        quick_date_layout.addWidget(self.last_week_btn, 0, 0)
        quick_date_layout.addWidget(self.last_month_btn, 0, 1)
        quick_date_layout.addWidget(self.last_3months_btn, 1, 0)
        quick_date_layout.addWidget(self.last_6months_btn, 1, 1)
        quick_date_layout.addWidget(self.last_year_btn, 2, 0)
        quick_date_layout.addWidget(self.max_range_btn, 2, 1)
        
        date_layout.addWidget(quick_date_frame)
        
        # Özel tarih seçimi
        custom_date_frame = QFrame()
        custom_date_layout = QGridLayout(custom_date_frame)
        
        from_date_label = QLabel("From:")
        self.from_date = QDateTimeEdit()
        self.from_date.setDateTime(QDateTime.currentDateTime().addYears(-1))
        self.from_date.setCalendarPopup(True)
        
        to_date_label = QLabel("To:")
        self.to_date = QDateTimeEdit()
        self.to_date.setDateTime(QDateTime.currentDateTime())
        self.to_date.setCalendarPopup(True)
        
        custom_date_layout.addWidget(from_date_label, 0, 0)
        custom_date_layout.addWidget(self.from_date, 0, 1)
        custom_date_layout.addWidget(to_date_label, 1, 0)
        custom_date_layout.addWidget(self.to_date, 1, 1)
        
        date_layout.addWidget(custom_date_frame)
        left_layout.addWidget(date_group)
        
        # Strateji parametreleri grubu
        self.backtest_params_frame = QFrame()
        self.backtest_params_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #424242;
                border-radius: 5px;
                padding: 10px;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit {
                padding: 5px;
                min-width: 100px;
            }
        """)
        backtest_params_layout = QGridLayout(self.backtest_params_frame)
        
        # RSI parametreleri
        self.backtest_rsi_length = QLineEdit("14")
        self.backtest_rsi_overbought = QLineEdit("70")
        self.backtest_rsi_oversold = QLineEdit("30")
        
        backtest_params_layout.addWidget(QLabel("RSI Length:"), 0, 0)
        backtest_params_layout.addWidget(self.backtest_rsi_length, 0, 1)
        backtest_params_layout.addWidget(QLabel("Overbought:"), 1, 0)
        backtest_params_layout.addWidget(self.backtest_rsi_overbought, 1, 1)
        backtest_params_layout.addWidget(QLabel("Oversold:"), 2, 0)
        backtest_params_layout.addWidget(self.backtest_rsi_oversold, 2, 1)
        
        # MACD parametreleri
        self.backtest_macd_fast = QLineEdit("12")
        self.backtest_macd_slow = QLineEdit("26")
        self.backtest_macd_signal = QLineEdit("9")
        
        backtest_params_layout.addWidget(QLabel("MACD Fast:"), 0, 2)
        backtest_params_layout.addWidget(self.backtest_macd_fast, 0, 3)
        backtest_params_layout.addWidget(QLabel("MACD Slow:"), 1, 2)
        backtest_params_layout.addWidget(self.backtest_macd_slow, 1, 3)
        backtest_params_layout.addWidget(QLabel("MACD Signal:"), 2, 2)
        backtest_params_layout.addWidget(self.backtest_macd_signal, 2, 3)
        
        left_layout.addWidget(self.backtest_params_frame)
        
        # Initial capital input
        capital_frame = QFrame()
        capital_layout = QHBoxLayout(capital_frame)
        
        capital_label = QLabel("Initial Capital (USDT):")
        capital_label.setStyleSheet("font-weight: bold;")
        self.capital_input = QLineEdit()
        self.capital_input.setText("100000")
        self.capital_input.setStyleSheet("padding: 5px; min-width: 150px;")
        
        capital_layout.addWidget(capital_label)
        capital_layout.addWidget(self.capital_input)
        capital_layout.addStretch()
        
        left_layout.addWidget(capital_frame)
        
        # Run backtest button
        self.run_backtest_button = QPushButton("Run Backtest")
        self.run_backtest_button.setStyleSheet("""
            QPushButton {
                background-color: #0d47a1;
                color: white;
                padding: 10px;
                font-weight: bold;
                font-size: 12pt;
                border-radius: 5px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0a3d8f;
            }
        """)
        self.run_backtest_button.clicked.connect(self.run_backtest)
        
        left_layout.addWidget(self.run_backtest_button, alignment=Qt.AlignCenter)
        left_layout.addStretch()
        
        # Sağ panel - Grafik ve sonuçlar
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        
        # Backtest grafiği
        self.backtest_chart = TradingChart()
        right_layout.addWidget(self.backtest_chart)
        
        # Backtest sonuçları
        self.backtest_results = QLabel("Backtest Results will appear here")
        self.backtest_results.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                padding: 15px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 11pt;
            }
        """)
        self.backtest_results.setWordWrap(True)
        right_layout.addWidget(self.backtest_results)
        
        # Ana layout'a panelleri ekle
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)  # Sağ panel daha geniş
        
        layout.addWidget(splitter, 0, 0)
        
        # Connect date range buttons
        self.last_week_btn.clicked.connect(lambda: self.set_date_range(7))
        self.last_month_btn.clicked.connect(lambda: self.set_date_range(30))
        self.last_3months_btn.clicked.connect(lambda: self.set_date_range(90))
        self.last_6months_btn.clicked.connect(lambda: self.set_date_range(180))
        self.last_year_btn.clicked.connect(lambda: self.set_date_range(365))
        self.max_range_btn.clicked.connect(self.set_max_date_range)
        
        # Hide strategy parameters initially
        self.hide_backtest_strategy_params()

    def set_date_range(self, days):
        """Set date range for backtest"""
        end_date = QDateTime.currentDateTime()
        start_date = end_date.addDays(-days)
        self.from_date.setDateTime(start_date)
        self.to_date.setDateTime(end_date)
        
    def set_max_date_range(self):
        """Set maximum available date range for backtest"""
        end_date = QDateTime.currentDateTime()
        start_date = end_date.addYears(-5)  # Maximum 5 years
        self.from_date.setDateTime(start_date)
        self.to_date.setDateTime(end_date)
        
    def hide_backtest_strategy_params(self):
        """Hide all backtest strategy parameters"""
        for i in range(self.backtest_params_frame.layout().count()):
            widget = self.backtest_params_frame.layout().itemAt(i).widget()
            if widget:
                widget.hide()
                
    def show_backtest_rsi_params(self):
        """Show RSI parameters for backtest"""
        self.hide_backtest_strategy_params()
        for i in range(6):  # First 6 widgets are RSI related
            widget = self.backtest_params_frame.layout().itemAt(i).widget()
            if widget:
                widget.show()
                
    def show_backtest_macd_params(self):
        """Show MACD parameters for backtest"""
        self.hide_backtest_strategy_params()
        for i in range(6, 12):  # Last 6 widgets are MACD related
            widget = self.backtest_params_frame.layout().itemAt(i).widget()
            if widget:
                widget.show()
                
    def on_backtest_strategy_changed(self, strategy):
        """Handle backtest strategy selection changes"""
        if strategy == "RSI":
            self.show_backtest_rsi_params()
        elif strategy == "MACD":
            self.show_backtest_macd_params()
        else:
            self.hide_backtest_strategy_params()

    def run_backtest(self):
        """Run backtest with current settings"""
        try:
            # Get date range
            start_timestamp = int(self.from_date.dateTime().toSecsSinceEpoch() * 1000)
            end_timestamp = int(self.to_date.dateTime().toSecsSinceEpoch() * 1000)
            
            # Get current settings
            symbol = self.backtest_symbol_combo.currentText()
            interval = self.backtest_interval_combo.currentText()
            strategy = self.backtest_strategy_combo.currentText()
            
            # Run backtest
            self.trading_bot.symbol = symbol
            self.trading_bot.interval = interval
            trades = self.trading_bot.backtest(
                start_time=start_timestamp,
                end_time=end_timestamp,
                strategy_type=strategy
            )
            
            if trades:
                # Calculate statistics
                total_trades = len(trades)
                winning_trades = len([t for t in trades if t['profit'] > 0])
                total_profit = sum(t['profit'] for t in trades)
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                # Update results
                self.backtest_results.setText(f"Backtest Results ({interval}):\n"
                                               f"Total Trades: {total_trades}\n"
                                               f"Winning Trades: {winning_trades}\n"
                                               f"Win Rate: {win_rate:.2f}%\n"
                                               f"Total Profit: {total_profit:.2f} USDT")
                
                # Get historical data for chart
                data = self.trading_bot.get_historical_data(
                    symbol=symbol,
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    interval=interval
                )
                
                if data is not None:
                    # Calculate indicators based on strategy
                    indicators = {}
                    if strategy == "Special":
                        ap = (data['high'] + data['low'] + data['close']) / 3
                        esa = ta.ema(close=ap, length=10)
                        d = ta.ema(close=abs(ap - esa), length=10)
                        ci = (ap - esa) / (0.015 * d)
                        indicators['wt1'] = ta.ema(close=ci, length=21)
                        indicators['wt2'] = ta.sma(close=indicators['wt1'], length=4)
                    elif strategy == "RSI":
                        indicators['rsi'] = ta.rsi(close=data['close'], length=14)
                    elif strategy == "MACD":
                        macd = ta.macd(close=data['close'], fast=12, slow=26, signal=9)
                        indicators['macd'] = macd['MACD_12_26_9']
                        indicators['signal'] = macd['MACDs_12_26_9']
                        indicators['histogram'] = macd['MACDh_12_26_9']
                    
                    # Update chart
                    self.backtest_chart.clear()
                    self.backtest_chart.update_chart(data, strategy_type=strategy, indicators=indicators)
                    
                    # Add trade markers
                    for trade in trades:
                        self.backtest_chart.add_trade_marker(
                            trade['timestamp'],
                            trade['price'],
                            trade['type']
                        )
                    
                    # Adjust chart layout
                    self.backtest_chart.figure.tight_layout()
                    self.backtest_chart.canvas.draw()
            else:
                self.backtest_results.setText("No trades executed during backtest period")
                
        except Exception as e:
            self.backtest_results.setText(f"Error during backtest: {str(e)}")
            traceback.print_exc()

    def on_coin_search_changed(self, text):
        """Handle coin search changes"""
        if text:
            try:
                symbol = text.upper()
                self.current_symbol = symbol
                # Use existing trading bot instance
                self.trading_bot.symbol = symbol
                ticker = self.trading_bot.client.get_ticker(symbol=symbol)
                
                info = {
                    'price': float(ticker['lastPrice']),
                    'volume': float(ticker['volume']) * float(ticker['lastPrice']),
                    'price_change': float(ticker['priceChangePercent']),
                    'high': float(ticker['highPrice']),
                    'low': float(ticker['lowPrice'])
                }
                
                # Update coin info display
                self.coin_info_widget.update_info(info)
                
                # Update chart with new symbol
                try:
                    data = self.trading_bot.get_recent_data(symbol=symbol, interval=self.current_interval, limit=100)
                    wt1, wt2 = self.trading_bot.calculate_wave_trend(data)
                    self.chart_widget.update_chart(data, wt1, wt2)
                except Exception as e:
                    print(f"Chart update error on symbol change: {e}")
                
            except Exception as e:
                # Reset info if invalid symbol
                info = {
                    'price': 0,
                    'volume': 0,
                    'price_change': 0,
                    'high': 0,
                    'low': 0
                }
                self.coin_info_widget.update_info(info)

    def closeEvent(self, event):
        """Clean up when closing the application"""
        print("Closing application...")
        try:
            if self.trading_thread:
                print("Stopping trading thread...")
                self.trading_thread.stop()
                self.trading_thread.wait()
            if self.market_thread:
                print("Stopping market thread...")
                self.market_thread.stop()
                self.market_thread.wait()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        event.accept()

    def calculate_indicators(self, df):
        """Calculate technical indicators for a dataframe"""
        try:
            # Convert index to integer to avoid warnings
            df = df.copy()
            df.reset_index(inplace=True, drop=True)
            
            # RSI
            rsi = df.ta.rsi(close='close', length=14)
            if pd.isna(rsi.iloc[-1]):
                return None, None, None, None, None
            
            # Moving Averages
            sma20 = df.ta.sma(close='close', length=20)
            sma50 = df.ta.sma(close='close', length=50)
            
            if pd.isna(sma20.iloc[-1]) or pd.isna(sma50.iloc[-1]):
                return None, None, None, None, None
            
            # MACD
            macd = df.ta.macd(close='close', fast=12, slow=26, signal=9)
            if macd is None or macd.empty:
                return None, None, None, None, None
                
            macd_val = macd[f'MACD_12_26_9'].iloc[-1]
            macd_signal = macd[f'MACDs_12_26_9'].iloc[-1]
            
            if pd.isna(macd_val) or pd.isna(macd_signal):
                return None, None, None, None, None
                
            return rsi.iloc[-1], sma20.iloc[-1], sma50.iloc[-1], macd_val, macd_signal
            
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return None, None, None, None, None

    def setup_market_tab(self, tab):
        """Setup market overview tab"""
        layout = QVBoxLayout(tab)
        
        # Market stats
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        stats_layout = QGridLayout(stats_frame)
        
        # Market statistics labels
        self.total_market_cap = QLabel("Total Market Cap: -")
        self.total_volume = QLabel("24h Volume: -")
        self.btc_dominance = QLabel("BTC Dominance: -")
        self.eth_dominance = QLabel("ETH Dominance: -")
        self.top_gainers = QLabel("Top Gainers: -")
        self.top_losers = QLabel("Top Losers: -")
        self.top_volume = QLabel("Top Volume: -")
        self.market_sentiment = QLabel("Market Sentiment: -")
        
        # Style labels
        for label in [self.total_market_cap, self.total_volume, self.btc_dominance, 
                     self.eth_dominance, self.top_gainers, self.top_losers, 
                     self.top_volume, self.market_sentiment]:
            font = label.font()
            font.setPointSize(10)
            label.setFont(font)
        
        # Add labels to stats layout
        stats_layout.addWidget(self.total_market_cap, 0, 0)
        stats_layout.addWidget(self.total_volume, 0, 1)
        stats_layout.addWidget(self.btc_dominance, 1, 0)
        stats_layout.addWidget(self.eth_dominance, 1, 1)
        stats_layout.addWidget(self.market_sentiment, 2, 0)
        stats_layout.addWidget(self.top_volume, 2, 1)
        stats_layout.addWidget(self.top_gainers, 3, 0)
        stats_layout.addWidget(self.top_losers, 3, 1)
        
        layout.addWidget(stats_frame)
        
        # Market table
        self.market_table = QTableWidget()
        self.market_table.setColumnCount(10)
        self.market_table.setHorizontalHeaderLabels([
            "Symbol", "Price", "24h Change", "24h High", "24h Low", 
            "Volume (USDT)", "Market Cap", "Signal", "RSI", "Trend"
        ])
        
        # Style table
        self.market_table.setAlternatingRowColors(True)
        self.market_table.horizontalHeader().setStretchLastSection(True)
        self.market_table.verticalHeader().setVisible(False)
        self.market_table.setSortingEnabled(True)
        
        # Set column widths
        header = self.market_table.horizontalHeader()
        header.setSectionResizeMode(0, header.ResizeToContents)  # Symbol
        header.setSectionResizeMode(1, header.ResizeToContents)  # Price
        header.setSectionResizeMode(2, header.ResizeToContents)  # Change
        
        layout.addWidget(self.market_table)
        
        # Add market filter controls
        filter_frame = QFrame()
        filter_layout = QHBoxLayout(filter_frame)
        
        # Volume filter
        volume_label = QLabel("Min Volume (USDT):")
        self.volume_filter = QLineEdit()
        self.volume_filter.setPlaceholderText("1000000")
        
        # Change filter
        change_label = QLabel("Min Change (%):")
        self.change_filter = QLineEdit()
        self.change_filter.setPlaceholderText("5")
        
        # Market cap filter
        cap_label = QLabel("Min Market Cap (USDT):")
        self.cap_filter = QLineEdit()
        self.cap_filter.setPlaceholderText("10000000")
        
        # Apply filter button
        self.apply_filter_btn = QPushButton("Apply Filters")
        self.apply_filter_btn.clicked.connect(self.apply_market_filters)
        
        # Add to filter layout
        filter_layout.addWidget(volume_label)
        filter_layout.addWidget(self.volume_filter)
        filter_layout.addWidget(change_label)
        filter_layout.addWidget(self.change_filter)
        filter_layout.addWidget(cap_label)
        filter_layout.addWidget(self.cap_filter)
        filter_layout.addWidget(self.apply_filter_btn)
        
        layout.addWidget(filter_frame)

    def apply_market_filters(self):
        """Apply filters to market table"""
        try:
            min_volume = float(self.volume_filter.text() or "0")
            min_change = float(self.change_filter.text() or "0")
            min_cap = float(self.cap_filter.text() or "0")
            
            for row in range(self.market_table.rowCount()):
                volume = float(self.market_table.item(row, 5).text().replace(",", ""))
                change = float(self.market_table.item(row, 2).text().replace("%", ""))
                market_cap = float(self.market_table.item(row, 6).text().replace(",", ""))
                
                show_row = (volume >= min_volume and 
                           abs(change) >= min_change and 
                           market_cap >= min_cap)
                
                self.market_table.setRowHidden(row, not show_row)
                
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numbers for filters")

    def setup_strategy_tab(self, tab):
        """Setup strategy editor tab"""
        layout = QVBoxLayout(tab)
        
        # Strategy list frame
        list_frame = QFrame()
        list_layout = QVBoxLayout(list_frame)
        
        # Strategy list label
        list_label = QLabel("Custom Strategies")
        font = list_label.font()
        font.setPointSize(12)
        font.setBold(True)
        list_label.setFont(font)
        list_layout.addWidget(list_label)
        
        # Strategy list
        self.strategy_list = QTableWidget()
        self.strategy_list.setColumnCount(2)
        self.strategy_list.setHorizontalHeaderLabels(["Name", "Description"])
        self.strategy_list.horizontalHeader().setStretchLastSection(True)
        self.strategy_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.strategy_list.setSelectionMode(QTableWidget.SingleSelection)
        self.strategy_list.itemSelectionChanged.connect(self.on_strategy_selected)
        list_layout.addWidget(self.strategy_list)
        
        # Strategy editor frame
        editor_frame = QFrame()
        editor_layout = QVBoxLayout(editor_frame)
        
        # Strategy name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Strategy Name:")
        self.strategy_name_input = QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.strategy_name_input)
        editor_layout.addLayout(name_layout)
        
        # Strategy description input
        desc_layout = QHBoxLayout()
        desc_label = QLabel("Description:")
        self.strategy_desc_input = QLineEdit()
        desc_layout.addWidget(desc_label)
        desc_layout.addWidget(self.strategy_desc_input)
        editor_layout.addLayout(desc_layout)
        
        # Code editor
        editor_label = QLabel("Strategy Code:")
        self.strategy_editor = QTextEdit()
        self.strategy_editor.setFont(QFont("Courier", 10))
        self.strategy_editor.setPlaceholderText(
            "# Define your trading strategy here\n"
            "def custom_strategy(data):\n"
            "    # data is a pandas DataFrame with columns: open, high, low, close, volume\n"
            "    # Available indicators: RSI, SMA, EMA, MACD, etc. (using pandas_ta)\n"
            "    # Example:\n"
            "    rsi = data.ta.rsi(close='close', length=14).iloc[-1]\n"
            "    sma20 = data.ta.sma(close='close', length=20).iloc[-1]\n"
            "    \n"
            "    if rsi < 30 and data['close'].iloc[-1] > sma20:\n"
            "        return 'BUY'\n"
            "    elif rsi > 70 and data['close'].iloc[-1] < sma20:\n"
            "        return 'SELL'\n"
            "    \n"
            "    return 'NEUTRAL'\n"
        )
        editor_layout.addWidget(editor_label)
        editor_layout.addWidget(self.strategy_editor)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.new_strategy_btn = QPushButton("New Strategy")
        self.new_strategy_btn.clicked.connect(self.new_strategy)
        
        self.save_strategy_btn = QPushButton("Save Strategy")
        self.save_strategy_btn.clicked.connect(self.save_strategy)
        
        self.delete_strategy_btn = QPushButton("Delete Strategy")
        self.delete_strategy_btn.clicked.connect(self.delete_strategy)
        self.delete_strategy_btn.setEnabled(False)
        
        button_layout.addWidget(self.new_strategy_btn)
        button_layout.addWidget(self.save_strategy_btn)
        button_layout.addWidget(self.delete_strategy_btn)
        editor_layout.addLayout(button_layout)
        
        # Add frames to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(list_frame)
        splitter.addWidget(editor_frame)
        splitter.setStretchFactor(1, 2)  # Make editor frame twice as wide
        layout.addWidget(splitter)
        
    def load_custom_strategies(self):
        """Load custom strategies from strategies directory"""
        try:
            # Create strategies directory if it doesn't exist
            if not os.path.exists("strategies"):
                os.makedirs("strategies")
                
            # Load strategies
            self.custom_strategies = {}
            for file in os.listdir("strategies"):
                if file.endswith(".py"):
                    name = file[:-3]  # Remove .py extension
                    with open(os.path.join("strategies", file), "r") as f:
                        code = f.read()
                        # Extract description from first line comment if exists
                        desc = ""
                        lines = code.split("\n")
                        if lines and lines[0].startswith("#"):
                            desc = lines[0][1:].strip()
                        self.custom_strategies[name] = {
                            "code": code,
                            "description": desc
                        }
                        
            # Update strategy list
            self.update_strategy_list()
            
            # Update strategy combos
            self.update_strategy_combos()
            
        except Exception as e:
            print(f"Error loading custom strategies: {e}")
            traceback.print_exc()
            
    def update_strategy_list(self):
        """Update strategy list table"""
        self.strategy_list.setRowCount(len(self.custom_strategies))
        for i, (name, strategy) in enumerate(self.custom_strategies.items()):
            self.strategy_list.setItem(i, 0, QTableWidgetItem(name))
            self.strategy_list.setItem(i, 1, QTableWidgetItem(strategy["description"]))
            
    def update_strategy_combos(self):
        """Update strategy selection combos"""
        # Get current selections
        trading_strategy = self.strategy_combo.currentText()
        backtest_strategy = self.backtest_strategy_combo.currentText()
        
        # Update items
        strategies = ["Special", "RSI", "MACD"] + list(self.custom_strategies.keys())
        
        self.strategy_combo.clear()
        self.strategy_combo.addItems(strategies)
        
        self.backtest_strategy_combo.clear()
        self.backtest_strategy_combo.addItems(strategies)
        
        # Restore selections if they still exist
        index = self.strategy_combo.findText(trading_strategy)
        if index >= 0:
            self.strategy_combo.setCurrentIndex(index)
            
        index = self.backtest_strategy_combo.findText(backtest_strategy)
        if index >= 0:
            self.backtest_strategy_combo.setCurrentIndex(index)
            
    def new_strategy(self):
        """Clear strategy editor for new strategy"""
        self.strategy_name_input.clear()
        self.strategy_desc_input.clear()
        self.strategy_editor.clear()
        self.strategy_editor.setPlaceholderText(
            "# Define your trading strategy here\n"
            "def custom_strategy(data):\n"
            "    # data is a pandas DataFrame with columns: open, high, low, close, volume\n"
            "    # Available indicators: RSI, SMA, EMA, MACD, etc. (using pandas_ta)\n"
            "    # Example:\n"
            "    rsi = data.ta.rsi(close='close', length=14).iloc[-1]\n"
            "    sma20 = data.ta.sma(close='close', length=20).iloc[-1]\n"
            "    \n"
            "    if rsi < 30 and data['close'].iloc[-1] > sma20:\n"
            "        return 'BUY'\n"
            "    elif rsi > 70 and data['close'].iloc[-1] < sma20:\n"
            "        return 'SELL'\n"
            "    \n"
            "    return 'NEUTRAL'\n"
        )
        self.strategy_list.clearSelection()
        self.delete_strategy_btn.setEnabled(False)
        
    def save_strategy(self):
        """Save current strategy"""
        try:
            name = self.strategy_name_input.text().strip()
            if not name:
                raise ValueError("Please enter a strategy name")
                
            if not name.isalnum():
                raise ValueError("Strategy name must be alphanumeric")
                
            desc = self.strategy_desc_input.text().strip()
            code = self.strategy_editor.toPlainText().strip()
            
            if not code:
                raise ValueError("Please enter strategy code")
                
            if "def custom_strategy" not in code:
                raise ValueError("Strategy must contain 'custom_strategy' function")
                
            # Add description as comment if provided
            if desc:
                code = f"# {desc}\n{code}"
                
            # Save to file
            with open(os.path.join("strategies", f"{name}.py"), "w") as f:
                f.write(code)
                
            # Update strategies
            self.custom_strategies[name] = {
                "code": code,
                "description": desc
            }
            
            # Update UI
            self.update_strategy_list()
            self.update_strategy_combos()
            
            QMessageBox.information(self, "Success", "Strategy saved successfully!")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            
    def delete_strategy(self):
        """Delete selected strategy"""
        try:
            selected = self.strategy_list.selectedItems()
            if not selected:
                return
                
            name = selected[0].text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete strategy '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Delete file
                os.remove(os.path.join("strategies", f"{name}.py"))
                
                # Remove from strategies
                del self.custom_strategies[name]
                
                # Update UI
                self.update_strategy_list()
                self.update_strategy_combos()
                self.new_strategy()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            
    def on_strategy_selected(self):
        """Handle strategy selection"""
        selected = self.strategy_list.selectedItems()
        if not selected:
            return
            
        name = selected[0].text()
        strategy = self.custom_strategies[name]
        
        self.strategy_name_input.setText(name)
        self.strategy_desc_input.setText(strategy["description"])
        self.strategy_editor.setText(strategy["code"])
        self.delete_strategy_btn.setEnabled(True)

class MarketUpdateThread(QThread):
    signal_update = pyqtSignal(list)  # market data
    signal_stats = pyqtSignal(dict)   # market stats
    
    def __init__(self, bot):
        super().__init__()
        print("Initializing MarketUpdateThread...")
        self.bot = bot
        self.is_running = True
        
    def process_ticker(self, ticker, symbols_data):
        """Process a single ticker"""
        try:
            symbol = ticker['symbol']
            if symbol not in symbols_data:
                return None
                
            data = symbols_data[symbol]
            price = float(ticker['lastPrice'])
            volume = ticker['volume_usdt']
            change = float(ticker['priceChangePercent'])
            
            # Calculate indicators
            try:
                wt1, wt2 = self.bot.calculate_wave_trend(data)
                signal = self.bot.get_signal(wt1, wt2)
                
                rsi = data.ta.rsi(close='close', length=14).iloc[-1]
                sma20 = data.ta.sma(close='close', length=20).iloc[-1]
                
                if pd.isna(rsi) or pd.isna(sma20):
                    return None
                    
                if rsi > 50 and sma20 > data['close'].mean():
                    trend = "BULLISH"
                elif rsi < 50 and sma20 < data['close'].mean():
                    trend = "BEARISH"
                else:
                    trend = "NEUTRAL"
                    
            except Exception as e:
                print(f"Error calculating indicators for {symbol}: {e}")
                signal = "N/A"
                rsi = 50
                trend = "NEUTRAL"
            
            return {
                'symbol': symbol,
                'price': price,
                'change': change,
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'volume': volume,
                'signal': signal,
                'rsi': rsi,
                'trend': trend
            }
            
        except Exception as e:
            print(f"Error processing {ticker['symbol']}: {e}")
            return None

    def run(self):
        print("MarketUpdateThread started running")
        error_count = 0
        while self.is_running:
            try:
                print("\nFetching market data...")
                # Get market data
                tickers = self.bot.client.get_ticker()
                print(f"Got {len(tickers)} tickers")
                
                if not tickers:
                    print("No tickers received!")
                    raise ValueError("No market data available")
                
                # Prepare data structures
                market_data = []
                total_volume = 0
                total_market_cap = 0
                btc_price = 0
                btc_market_cap = 0
                eth_market_cap = 0
                price_changes = []
                volumes = {}
                
                # Filter USDT pairs and calculate volumes in one pass
                high_volume_pairs = []
                for t in tickers:
                    try:
                        if t['symbol'].endswith('USDT'):
                            price = float(t['lastPrice'])
                            volume = float(t['volume']) * price
                            if volume > 5000000:  # 5M USDT minimum volume
                                t['volume_usdt'] = volume
                                high_volume_pairs.append(t)
                                
                                symbol = t['symbol']
                                if symbol == 'BTCUSDT':
                                    btc_price = price
                                    btc_market_cap = volume
                                elif symbol == 'ETHUSDT':
                                    eth_market_cap = volume
                    except Exception as e:
                        print(f"Error processing ticker {t['symbol']}: {e}")
                        continue
                
                print(f"Processing {len(high_volume_pairs)} high volume pairs...")
                
                # Process pairs in smaller batches
                batch_size = 10
                for i in range(0, len(high_volume_pairs), batch_size):
                    batch = high_volume_pairs[i:i+batch_size]
                    for ticker in batch:
                        try:
                            symbol = ticker['symbol']
                            price = float(ticker['lastPrice'])
                            volume = ticker['volume_usdt']
                            change = float(ticker['priceChangePercent'])
                            
                            # Get recent data with fewer periods
                            self.bot.symbol = symbol
                            data = self.bot.get_recent_data(limit=20)
                            
                            if data is None or data.empty:
                                print(f"No data received for {symbol}")
                                continue
                            
                            # Calculate basic indicators
                            try:
                                rsi = data.ta.rsi(close='close', length=14).iloc[-1]
                                sma20 = data.ta.sma(close='close', length=20).iloc[-1]
                                
                                if pd.isna(rsi) or pd.isna(sma20):
                                    print(f"Invalid indicator values for {symbol}")
                                    continue
                                
                                # Simplified trend calculation
                                if rsi > 50 and data['close'].iloc[-1] > sma20:
                                    trend = "BULLISH"
                                elif rsi < 50 and data['close'].iloc[-1] < sma20:
                                    trend = "BEARISH"
                                else:
                                    trend = "NEUTRAL"
                                
                                # Simplified signal based on RSI
                                if rsi < 30:
                                    signal = "BUY"
                                elif rsi > 70:
                                    signal = "SELL"
                                else:
                                    signal = "NEUTRAL"
                                
                                # Add to market data
                                market_data.append({
                                    'symbol': symbol,
                                    'price': price,
                                    'change': change,
                                    'high': float(ticker['highPrice']),
                                    'low': float(ticker['lowPrice']),
                                    'volume': volume,
                                    'signal': signal,
                                    'rsi': rsi,
                                    'trend': trend
                                })
                                
                                total_volume += volume
                                total_market_cap += volume
                                price_changes.append((symbol, change))
                                volumes[symbol] = volume
                                
                            except Exception as e:
                                print(f"Error calculating indicators for {symbol}: {e}")
                                continue
                                
                        except Exception as e:
                            print(f"Error processing {symbol}: {e}")
                            continue
                    
                    # Emit partial updates for better responsiveness
                    if market_data:
                        print(f"Processed {len(market_data)} pairs successfully...")
                        self.signal_update.emit(market_data.copy())
                
                if not market_data:
                    print("No market data was processed successfully!")
                    raise ValueError("Failed to process any market data")
                
                # Sort by volume
                market_data.sort(key=lambda x: x['volume'], reverse=True)
                
                # Calculate stats
                stats = {
                    'total_volume': total_volume,
                    'total_market_cap': total_market_cap,
                    'btc_price': btc_price,
                    'btc_market_cap': btc_market_cap,
                    'eth_market_cap': eth_market_cap,
                    'price_changes': price_changes,
                    'volumes': volumes
                }
                
                # Final update
                print(f"Emitting final data for {len(market_data)} pairs...")
                self.signal_update.emit(market_data)
                self.signal_stats.emit(stats)
                print("Market data update completed")
                
                # Reset error count on successful update
                error_count = 0
                
            except Exception as e:
                error_count += 1
                print(f"Market update error: {e}")
                traceback.print_exc()
                
                if error_count >= 3:
                    print("Too many consecutive errors, stopping market updates")
                    self.stop()
                    break
            
            # Sleep for 30 seconds
            print("Sleeping for 30 seconds...")
            for i in range(30):
                if not self.is_running:
                    break
                if i % 5 == 0:
                    print(f"Next update in {30-i} seconds...")
                self.sleep(1)
    
    def stop(self):
        print("Stopping MarketUpdateThread...")
        self.is_running = False

def main():
    try:
        print("Starting application...")
        app = QApplication(sys.argv)
        print("QApplication created")
        
        print("Creating main window...")
        window = TradingGUI()
        print("Main window created")
        
        print("Showing main window...")
        window.show()
        print("Main window shown")
        
        print("Entering event loop...")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Critical error in main: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("Starting main...")
    main()