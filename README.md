# FA Stock Analysis Tool

## Overview
FA Stock Analysis Tool is a Python-based application designed for financial market enthusiasts and investors. It provides an analysis of stocks using various valuation methods, including the Discounted Cash Flow (DCF) Ratio. The tool is versatile, allowing users to analyze a pre-defined list like the NYSE Fortune 500 or any custom list of stocks uploaded by the user. Additionally, it offers flexibility in choosing the Margin of Safety (MOS) for investment evaluations.

## Features
- **Custom Stock Lists:** Users can upload their stock list for analysis, making the tool adaptable for different market portfolios.
- **Multiple Valuation Methods:** Includes various stock valuation methods to offer a comprehensive financial analysis.
- **Margin of Safety Selection:** Users can select different Margin of Safety percentages to tailor the analysis to their risk preferences.
- **Interactive GUI:** A user-friendly interface facilitates easy interaction with the tool's features.

## Setup and Usage

### Prerequisites
- Python 3.x
- Required Python libraries: `requests`, `yfinance`, `pandas`, `tkinter`
- An AlphaVantage API key ([sign up here](https://www.alphavantage.co/support/#api-key) for a free key)

### Installation
1. Clone the repository to your local machine: git clone https://github.com/dalibyte/FortunAnalytica/stock_analyzer.py
2. Install the required Python libraries: pip install requests yfinance pandas

### Running the Application
1. Open the application by running `stock_analyzer.py`.
2. Enter your AlphaVantage API key in the provided field.
3. Upload your stock list by clicking 'Load Stock List' and selecting your file.
- The file should contain stock symbols in the first column, labeled 'Symbol'.
4. Select your desired Margin of Safety percentage by clicking one of the MOS buttons.
5. Click 'Analyze Stocks' to start the analysis.

### Features in Detail
- **Custom Stock List Upload:** You can analyze different stocks by uploading a CSV file. This can be the Fortune 500 list or any list of your choice.
- **Margin of Safety Options:** Choose between low (20%), medium (40%), and high (60%) Margin of Safety to align the analysis with your investment risk tolerance.
- **Interactive Results:** The analysis results are displayed in an easy-to-read format, showing the valuation and investibility of each stock based on the chosen MOS.

## Contributing
Contributions to enhance the functionality and efficiency of this tool are welcome. Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## Disclaimer
This tool is for educational and informational purposes only and is not intended as financial advice.
