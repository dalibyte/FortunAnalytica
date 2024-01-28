# Fortune 500 Stock Analyzer

## Overview
This Python application analyzes NYSE Fortune 500 stocks using the Discounted Cash Flow (DCF) Ratio valuation method, comparing them with current market prices. It relies on financial data from the free AlphaVantage API.

## Features
- Analyzes NYSE Fortune 500 stock list.
- Uses DCF Ratio for stock valuation.
- Real-time data from AlphaVantage API.
- User-friendly GUI interface.

## How It Works
The app fetches data for each Fortune 500 company from AlphaVantage, calculates the DCF Ratio, and compares it to the market price, identifying potential investment opportunities.

## Setup and Usage

### Prerequisites
- Python 3.x
- Libraries: `requests`, `yfinance`, `pandas`, `tkinter`
- AlphaVantage API key ([Get a free key](https://www.alphavantage.co/support/#api-key))

### Installation
1. Clone the repo:
git clone [repo-link]

2. Install dependencies:
pip install requests yfinance pandas

### Running the Application
1. Run `stock_analyzer.py`.
2. Enter your AlphaVantage API key in the GUI.
3. Click 'Analyze Stocks'.

## Contributing
Contributions are welcome. Please fork the repo and submit a pull request.

## License
MIT License - see [LICENSE](LICENSE) file.

## Disclaimer
For educational purposes only. Not financial advice.
