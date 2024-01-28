# Stock Analysis Tool with API List Support

## Overview
`stock_analysis_API_LIST.py` is an advanced version of the stock analysis tool, capable of processing extensive stock lists like the Fortune 500 in a single session. This functionality is achieved through the support of multiple AlphaVantage API keys.

## Features
- **Multiple API Key Support:** Allows loading and utilization of multiple AlphaVantage API keys to enable comprehensive analysis of large stock lists.
- **Automated API Key Switching:** Automatically switches to the next API key once the request limit of the current key is reached, ensuring continuous analysis.
- **User-Friendly Interface:** Easy loading of both stock list and API keys through a graphical user interface.

## Usage

### Preparing API Keys
Ensure you have at least 20 AlphaVantage API keys for full coverage of the Fortune 500 list. Store each key on a separate line in a text file.

### Running the Tool
1. Start `stock_analysis_API_LIST.py`.
2. Use the 'Load API Keys' button to load your file containing multiple API keys.
3. Load your stock list file (e.g., Fortune 500) using the 'Load Stock List' button.
4. Select your desired Margin of Safety.
5. Click 'Analyze Stocks' to start the analysis.

### Viewing Results
The tool displays the DCF Ratio and investibility status ('Yes' or 'No') based on the selected Margin of Safety for each stock.

## Limitations and Considerations
- Designed for AlphaVantage's free API tier, allowing up to 25 requests per day for each API key.
- Careful management of multiple API keys is required to comply with AlphaVantage's terms of service.
- A premium AlphaVantage subscription is recommended for higher request volumes and more frequent updates.

