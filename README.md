# FortunAnalytica

A quantitative stock screening engine that estimates intrinsic value using **Discounted Cash Flow (DCF) analysis** with WACC-based discounting and Gordon Growth terminal value modeling. Built for fundamental analysis of NYSE/NASDAQ equities.

## How It Works

FortunAnalytica pulls live financial data from **AlphaVantage** (cash flows, balance sheets) and **Yahoo Finance** (market data, beta), then runs a two-stage DCF model for each stock:

1. **Free Cash Flow Estimation** — Computes FCF (Operating Cash Flow − CapEx) over 5 years of historical data, calculates CAGR with growth-rate clamping
2. **WACC Calculation** — Estimates Weighted Average Cost of Capital using CAPM for cost of equity, balance sheet data for capital structure, and a 21% corporate tax rate assumption
3. **Two-Stage DCF** — Projects FCFs with linearly decaying growth rates, then applies a Gordon Growth Model terminal value
4. **Net Debt Adjustment** — Converts enterprise value to equity value per share
5. **Signal Classification** — Compares DCF-implied price against market price with configurable margin of safety → `BUY` / `HOLD` / `OVERVALUED`

## Key Features

- **WACC-based discounting** (not a flat discount rate) using CAPM beta, debt structure, and market risk premium
- **Terminal value** via Gordon Growth Model with GDP-proxy perpetuity growth
- **Growth rate decay** — aggressive near-term growth fades to terminal rate over the projection window
- **Net debt adjustment** for enterprise-to-equity bridge
- **Rate-limited API client** with retry logic and error handling
- **CSV export** of full valuation data for further analysis
- **Visualization** — price vs. intrinsic value bar charts and sector signal breakdowns
- **CLI interface** with environment variable support for API keys

## Quick Start

```bash
pip install -r requirements.txt
export ALPHAVANTAGE_API_KEY="your_key_here"
python stock_analyzer.py fortune500
```

Or run interactively:
```bash
python stock_analyzer.py
```

## Output

| File | Description |
|------|-------------|
| `valuation_results.csv` | Full valuation data for all screened stocks |
| `valuation_chart.png` | Price vs. DCF intrinsic value comparison |
| `sector_breakdown.png` | Signal distribution across sectors |

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk-Free Rate | 4.3% | 10-year Treasury yield proxy |
| Market Return | 10.0% | Long-run S&P 500 average return |
| Projection Years | 10 | DCF projection horizon |
| Terminal Growth | 2.5% | Perpetuity growth rate (GDP proxy) |
| Margin of Safety | 30% | Required discount to intrinsic value for BUY signal |

## Assumptions & Limitations

- DCF models are inherently forward-looking and sensitive to growth rate assumptions
- WACC estimation uses a simplified cost-of-debt proxy (5% default) when interest expense data is unavailable
- AlphaVantage free tier is limited to 5 API calls/minute (25 calls/day), which constrains screening throughput
- Historical FCF may not reflect future cash generation for high-growth or cyclical companies
- This tool is for educational and analytical purposes — not financial advice

## Tech Stack

- **Python 3.10+**
- **yfinance** — Market data and company fundamentals
- **AlphaVantage API** — Financial statements (cash flow, balance sheet, income statement)
- **pandas** — Data manipulation and export
- **matplotlib** — Visualization

## License

GPL-2.0 — See [LICENSE](LICENSE) for details.
