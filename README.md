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

## Limitations and Usage
Due to the AlphaVantage API's limit of 25 free requests per day, the application is designed to process a batch of 25 stocks at a time. It automatically saves the progress and requires a manual restart the next day to continue the analysis.

### Daily Restart Requirement
- The application processes up to 25 stocks in each run.
- After reaching the limit, it saves the progress and stops.
- **Manual Restart:** Users need to manually restart the application on the next day to continue analyzing the next batch of stocks.

## Setup and Usage

### Prerequisites
- Python 3.x
- Libraries: `requests`, `yfinance`, `pandas`, `tkinter`
- AlphaVantage API key ([Get a free key](https://www.alphavantage.co/support/#api-key))

### Installation
1. Clone the repo: git clone [repo-link]
2. Install dependencies: pip install requests yfinance pandas


### Running the Application
1. Run `stock_analyzer.py`.
2. Enter your AlphaVantage API key in the GUI.
3. Click 'Analyze Stocks'.
4. Restart the application the next day to continue with the next batch of stocks.

## Contributing
Contributions are welcome. Please fork the repo and submit a pull request.

## License
This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer
For educational purposes only. Not financial advice.
