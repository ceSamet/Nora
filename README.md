# Nora

A sophisticated cryptocurrency trading bot with a modern GUI interface for automated trading on Binance. The bot implements Wave Trend and other technical indicators for trading signals.

## Features

- Real-time cryptocurrency price monitoring
- Advanced technical analysis with Wave Trend indicator
- Interactive trading charts
- Market scanner for finding trading opportunities
- Custom trading strategy support
- User-friendly GUI interface
- Real-time market statistics and trends

## Requirements

- Python 3.8+
- Binance account with API keys

## Installation

1. Clone the repository:
```bash
git clone https://github.com/ceSamet/Nora.git
cd Nora
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `config.txt` file in the root directory with your Binance API keys:
```
your_api_key
your_api_secret
```

## Usage

Run the trading bot with GUI:
```bash
python trading_gui.py
```

## Custom Strategies

You can create custom trading strategies by adding Python files to the `strategies` directory. See `strategies/example.py` for an example strategy implementation.

## Disclaimer

This software is for educational purposes only. Use it at your own risk. The creators are not responsible for any financial losses incurred through the use of this software.

## License

MIT License 
