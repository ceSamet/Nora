from PyQt5.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.dates as mdates
import traceback

class TradingChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create figure and canvas
        self.figure = Figure(figsize=(12, 8), dpi=100, facecolor='#1e1e1e')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        # Create layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        # Initialize variables
        self.axes = []  # List to store all axes
        self.trade_markers = []  # List to store trade markers
        
        # Define style
        self.style = mpf.make_mpf_style(
            base_mpf_style='charles',
            gridstyle='--',
            gridcolor='#424242',
            gridaxis='both',
            facecolor='#1e1e1e',
            edgecolor='#424242',
            figcolor='#1e1e1e',
            y_on_right=False,
            rc={
                'axes.labelcolor': 'white',
                'axes.edgecolor': '#424242',
                'xtick.color': 'white',
                'ytick.color': 'white',
                'text.color': 'white',
                'figure.facecolor': '#1e1e1e',
                'figure.edgecolor': '#1e1e1e',
                'savefig.facecolor': '#1e1e1e',
                'savefig.edgecolor': '#1e1e1e',
                'grid.color': '#424242',
                'grid.linestyle': '--',
                'grid.alpha': 0.3
            },
            marketcolors=mpf.make_marketcolors(
                up='#26a69a',
                down='#ef5350',
                edge='inherit',
                wick='inherit',
                volume='in',
                ohlc='inherit'
            ),
            style_name='custom_dark'
        )
        
    def clear(self):
        """Clear all plots from the chart"""
        if self.figure:
            self.figure.clear()
            self.axes = []
            self.trade_markers = []
            self.canvas.draw()
            
    def create_subplots(self, strategy_type):
        """Create subplots based on strategy type"""
        self.figure.clear()
        
        if isinstance(strategy_type, pd.Series):
            strategy_type = str(strategy_type.iloc[0]) if not strategy_type.empty else "Special"
        strategy_type = str(strategy_type)  # Convert to string
        
        # Sadece iki subplot: Fiyat ve Hacim
        self.axes = [
            self.figure.add_subplot(211),  # Price
            self.figure.add_subplot(212)   # Volume
        ]
            
    def update_chart(self, data, strategy_type="Special", indicators=None):
        """Update chart with new data and indicators"""
        try:
            # Prepare data
            df = data.copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Clear previous plots
            self.figure.clear()
            
            # Create subplots with adjusted heights and spacing
            gs = self.figure.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0)
            self.axes = [
                self.figure.add_subplot(gs[0]),  # Price (larger)
                self.figure.add_subplot(gs[1])   # Volume (smaller)
            ]
            
            # Calculate optimal bar width based on data points
            time_diff = df.index[1] - df.index[0]
            width = 0.8 * (time_diff.total_seconds() / (24 * 60 * 60))  # 80% of time interval
            
            # Plot candlesticks
            up = df[df.close >= df.open]
            down = df[df.close < df.open]
            
            def plot_candlestick(data, color):
                # Plot bodies
                self.axes[0].vlines(data.index, data.low, data.high, color=color, linewidth=1)
                self.axes[0].vlines(data.index, data.open, data.close, color=color, linewidth=4)
            
            plot_candlestick(up, '#26a69a')    # Green candles
            plot_candlestick(down, '#ef5350')   # Red candles
            
            # Plot volume
            if 'volume' in df.columns:
                volume_colors = np.where(df.close >= df.open, '#26a69a', '#ef5350')
                self.axes[1].bar(df.index, df.volume, width=width, color=volume_colors, alpha=0.5)
                
                # Format volume axis
                self.axes[1].set_ylabel('Volume', color='white', fontsize=8, labelpad=5)
                volume_max = df.volume.max()
                self.axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/volume_max:.1%}'))
            
            # Add indicators on a separate axis
            if isinstance(indicators, dict) and indicators:
                ax_ind = self.axes[0].twinx()
                
                if strategy_type == "Special" and 'wt1' in indicators and 'wt2' in indicators:
                    ax_ind.plot(df.index, indicators['wt1'], '#2196f3', label='WT1', linewidth=0.8)
                    ax_ind.plot(df.index, indicators['wt2'], '#f44336', label='WT2', linewidth=0.8)
                    ax_ind.axhline(y=60, color='#f44336', linestyle='--', alpha=0.2, linewidth=0.8)
                    ax_ind.axhline(y=-60, color='#4caf50', linestyle='--', alpha=0.2, linewidth=0.8)
                    ax_ind.set_ylabel('Wave Trend', color='white', fontsize=8, labelpad=5)
                
                elif strategy_type == "RSI" and 'rsi' in indicators:
                    ax_ind.plot(df.index, indicators['rsi'], '#9c27b0', label='RSI', linewidth=0.8)
                    ax_ind.axhline(y=70, color='#f44336', linestyle='--', alpha=0.2, linewidth=0.8)
                    ax_ind.axhline(y=30, color='#4caf50', linestyle='--', alpha=0.2, linewidth=0.8)
                    ax_ind.set_ylim(0, 100)
                    ax_ind.set_ylabel('RSI', color='white', fontsize=8, labelpad=5)
                
                elif strategy_type == "MACD" and all(k in indicators for k in ['macd', 'signal']):
                    ax_ind.plot(df.index, indicators['macd'], '#2196f3', label='MACD', linewidth=0.8)
                    ax_ind.plot(df.index, indicators['signal'], '#f44336', label='Signal', linewidth=0.8)
                    ax_ind.set_ylabel('MACD', color='white', fontsize=8, labelpad=5)
                
                # Format indicator axis
                ax_ind.legend(loc='upper right', framealpha=0.0, fontsize=8)
                ax_ind.grid(False)
                ax_ind.tick_params(axis='y', colors='white', labelsize=8)
            
            # Format price axis
            self.axes[0].set_ylabel('Price', color='white', fontsize=8, labelpad=5)
            self.axes[0].tick_params(axis='y', colors='white', labelsize=8)
            
            # Format both axes
            for ax in self.axes:
                # Grid
                ax.grid(True, color='#424242', linestyle='--', alpha=0.2, which='both')
                ax.set_facecolor('#1e1e1e')
                
                # X-axis format
                ax.tick_params(axis='x', colors='white', labelsize=8, rotation=45)
                
                # Only show x-labels on bottom plot
                if ax == self.axes[0]:
                    ax.tick_params(axis='x', labelbottom=False)
                
                # Remove spines
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['bottom'].set_color('#424242')
                ax.spines['left'].set_color('#424242')
            
            # Date formatting
            locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
            formatter = mdates.DateFormatter('%Y-%m-%d\n%H:%M')
            self.axes[1].xaxis.set_major_locator(locator)
            self.axes[1].xaxis.set_major_formatter(formatter)
            
            # Adjust layout
            self.figure.subplots_adjust(left=0.12, right=0.88, bottom=0.15, top=0.95)
            
            # Draw
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating chart: {e}")
            traceback.print_exc()
            
    def add_trade_marker(self, timestamp, price, trade_type):
        """Add trade marker to the chart"""
        if not self.axes:
            return
            
        try:
            # Convert timestamp to datetime
            if isinstance(timestamp, (int, float)):
                timestamp = pd.to_datetime(timestamp, unit='ms')
            elif isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            # Set marker properties
            if trade_type == 'BUY':
                marker = '^'  # Triangle up
                color = '#26a69a'  # Green
                size = 100
            else:  # SELL
                marker = 'v'  # Triangle down
                color = '#ef5350'  # Red
                size = 100
            
            # Add marker
            scatter = self.axes[0].scatter(timestamp, price, 
                                         marker=marker, 
                                         s=size, 
                                         c=color, 
                                         alpha=0.7,
                                         zorder=5)
            
            self.trade_markers.append(scatter)
            self.canvas.draw()
            
        except Exception as e:
            print(f"Error adding trade marker: {e}")
            traceback.print_exc() 