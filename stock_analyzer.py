"""
FortunAnalytica - DCF Stock Valuation Engine
=============================================
A quantitative stock screening tool that estimates intrinsic value using
Discounted Cash Flow (DCF) analysis with WACC-based discounting and
Gordon Growth terminal value. Pulls live financial data from AlphaVantage
and Yahoo Finance, scores investment attractiveness, and exports results
to CSV with optional visualization.

Author: Jonathan Stewart (dalibyte)
License: GPL-2.0
"""

import requests
import yfinance as yf
try:
    from yfinance import cache
    cache._TzDBMng = type('_FakeDB', (), {
        '__init__': lambda *a, **k: None,
        'get_tz': lambda *a: None,
        'set_tz': lambda *a: None,
    })()
    cache._TzCacheManager = type('_FakeCM', (), {
        '__init__': lambda *a, **k: None,
        'get_tz': lambda *a: None,
        'set_tz': lambda *a: None,
    })
except Exception:
    pass
try:
    import yfinance.cache as yfc
    yfc._TzDBMng = type('_FakeDB', (), {
        '__init__': lambda *a, **k: None,
        'get_tz': lambda *a: None,
        'set_tz': lambda *a: None,
    })()
except Exception:
    pass
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import logging
import time
import os
import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_RISK_FREE_RATE = 0.043       # 10-yr Treasury proxy
DEFAULT_MARKET_RETURN = 0.10         # Long-run S&P 500 avg
DEFAULT_PROJECTION_YEARS = 10
DEFAULT_TERMINAL_GROWTH = 0.025      # Perpetuity growth rate (GDP proxy)
DEFAULT_MARGIN_OF_SAFETY = 0.30      # 30%
ALPHAVANTAGE_RATE_LIMIT = 5          # Free tier: 5 calls/min
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FortunAnalytica")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class StockValuation:
    """Holds the complete valuation result for a single ticker."""
    ticker: str
    company_name: str
    sector: str
    market_cap: float
    current_price: float
    shares_outstanding: float
    avg_fcf: float
    fcf_growth_rate: float
    wacc: float
    terminal_value: float
    dcf_enterprise_value: float
    dcf_per_share: float
    margin_of_safety_price: float
    upside_pct: float
    signal: str  # BUY / HOLD / OVERVALUED
    timestamp: str


# ---------------------------------------------------------------------------
# AlphaVantage API Client
# ---------------------------------------------------------------------------

class AlphaVantageClient:
    """Handles all AlphaVantage API interactions with rate limiting & retries."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._last_call = 0.0

    def _rate_limit(self):
        """Enforce minimum interval between API calls."""
        elapsed = time.time() - self._last_call
        wait = max(0, (60 / ALPHAVANTAGE_RATE_LIMIT) - elapsed)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()

    def _get(self, params: dict) -> Optional[dict]:
        """Execute a GET request with retries and error handling."""
        params["apikey"] = self.api_key
        for attempt in range(1, MAX_RETRIES + 1):
            self._rate_limit()
            try:
                resp = requests.get(self.BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                if "Error Message" in data:
                    log.warning("AV error: %s", data["Error Message"])
                    return None
                if "Note" in data:  # Rate limit hit
                    log.warning("AV rate limit hit, waiting 60s (attempt %d)", attempt)
                    time.sleep(60)
                    continue

                return data
            except requests.RequestException as e:
                log.warning("Request failed (attempt %d): %s", attempt, e)
                time.sleep(2 ** attempt)
        return None

    def get_cash_flow(self, symbol: str) -> Optional[list[dict]]:
        """Fetch annual cash flow statements."""
        data = self._get({"function": "CASH_FLOW", "symbol": symbol})
        if data and "annualReports" in data:
            return data["annualReports"]
        return None

    def get_balance_sheet(self, symbol: str) -> Optional[list[dict]]:
        """Fetch annual balance sheet data."""
        data = self._get({"function": "BALANCE_SHEET", "symbol": symbol})
        if data and "annualReports" in data:
            return data["annualReports"]
        return None

    def get_income_statement(self, symbol: str) -> Optional[list[dict]]:
        """Fetch annual income statements."""
        data = self._get({"function": "INCOME_STATEMENT", "symbol": symbol})
        if data and "annualReports" in data:
            return data["annualReports"]
        return None


# ---------------------------------------------------------------------------
# Valuation Engine
# ---------------------------------------------------------------------------

def safe_float(val, default=0.0) -> float:
    """Safely convert API values to float, handling None and 'None' strings."""
    if val is None or val == "None" or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_free_cash_flows(cash_flow_reports: list[dict], years: int = 5) -> list[float]:
    """
    Extract Free Cash Flow (Operating Cash Flow - CapEx) from annual reports.
    Returns most recent `years` values in chronological order (oldest first).
    """
    fcfs = []
    for report in cash_flow_reports[:years]:
        ocf = safe_float(report.get("operatingCashflow"))
        capex = safe_float(report.get("capitalExpenditures"))
        fcf = ocf - abs(capex)  # CapEx is sometimes reported as positive
        if ocf != 0:  # Skip years with no data
            fcfs.append(fcf)
    return list(reversed(fcfs))  # Chronological: oldest → newest


def compute_fcf_growth_rate(fcfs: list[float]) -> float:
    """
    Compute compound annual growth rate (CAGR) of free cash flows.
    Falls back to simple average growth if CAGR is not computable.
    """
    if len(fcfs) < 2:
        return 0.0

    # Filter out negative/zero starting values for CAGR
    if fcfs[0] > 0 and fcfs[-1] > 0:
        n = len(fcfs) - 1
        cagr = (fcfs[-1] / fcfs[0]) ** (1 / n) - 1
        return max(min(cagr, 0.30), -0.30)  # Clamp to +/-30%

    # Fallback: average YoY growth
    growths = []
    for i in range(1, len(fcfs)):
        if fcfs[i - 1] != 0:
            growths.append((fcfs[i] - fcfs[i - 1]) / abs(fcfs[i - 1]))
    if growths:
        avg = sum(growths) / len(growths)
        return max(min(avg, 0.30), -0.30)
    return 0.0


def estimate_wacc(
    ticker_info: dict,
    balance_sheet: Optional[list[dict]],
    risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    market_return: float = DEFAULT_MARKET_RETURN,
) -> float:
    """
    Estimate Weighted Average Cost of Capital.

    WACC = (E/V) * Re + (D/V) * Rd * (1 - Tc)

    Where:
        Re = Risk-free rate + Beta * (Market return - Risk-free rate)
        Rd = Interest expense / Total debt (approximated)
        Tc = Effective tax rate (approximated at 21% corporate rate)
    """
    beta = ticker_info.get("beta", 1.0) or 1.0
    market_cap = ticker_info.get("marketCap", 0) or 0

    # Cost of equity (CAPM)
    cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)

    # Cost of debt estimation
    total_debt = 0
    if balance_sheet:
        latest = balance_sheet[0]
        long_term = safe_float(latest.get("longTermDebt"))
        short_term = safe_float(latest.get("shortTermDebt"))
        total_debt = long_term + short_term

    cost_of_debt = 0.05  # Default assumption
    tax_rate = 0.21       # US corporate rate

    # Capital structure weights
    total_value = market_cap + total_debt
    if total_value == 0:
        return cost_of_equity  # All-equity fallback

    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value

    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    return max(wacc, 0.06)  # Floor at 6% to avoid unrealistic valuations


def dcf_valuation(
    avg_fcf: float,
    growth_rate: float,
    wacc: float,
    projection_years: int = DEFAULT_PROJECTION_YEARS,
    terminal_growth: float = DEFAULT_TERMINAL_GROWTH,
) -> tuple[float, float]:
    """
    Two-stage DCF model:
      Stage 1: Project FCFs forward at estimated growth rate, discount at WACC
      Stage 2: Gordon Growth Model terminal value

    Returns (enterprise_value, terminal_value)
    """
    if wacc <= terminal_growth:
        terminal_growth = wacc - 0.01  # Prevent division by zero / negative

    # Dampen aggressive growth assumptions over time
    pv_fcfs = 0.0
    projected_fcf = avg_fcf
    for year in range(1, projection_years + 1):
        # Growth rate decays linearly toward terminal growth
        blend = 1 - (year / projection_years)
        year_growth = (growth_rate * blend) + (terminal_growth * (1 - blend))
        projected_fcf *= (1 + year_growth)
        pv_fcfs += projected_fcf / ((1 + wacc) ** year)

    # Terminal value (Gordon Growth Model)
    terminal_fcf = projected_fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** projection_years)

    enterprise_value = pv_fcfs + pv_terminal
    return enterprise_value, terminal_value


def classify_signal(upside_pct: float, margin_of_safety: float) -> str:
    """Classify stock as BUY, HOLD, or OVERVALUED based on upside vs MOS."""
    if upside_pct >= margin_of_safety * 100:
        return "BUY"
    elif upside_pct >= 0:
        return "HOLD"
    else:
        return "OVERVALUED"


# ---------------------------------------------------------------------------
# Analysis Pipeline
# ---------------------------------------------------------------------------

def analyze_stock(
    ticker: str,
    av_client: AlphaVantageClient,
    margin_of_safety: float = DEFAULT_MARGIN_OF_SAFETY,
    projection_years: int = DEFAULT_PROJECTION_YEARS,
) -> Optional[StockValuation]:
    """Run full DCF valuation pipeline for a single ticker."""

    log.info("Analyzing %s...", ticker)

    # --- Yahoo Finance data ---
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
    except Exception as e:
        log.warning("yfinance failed for %s: %s", ticker, e)
        return None

    market_cap = info.get("marketCap")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding")
    company_name = info.get("shortName", ticker)
    sector = info.get("sector", "Unknown")

    if not all([market_cap, current_price, shares]):
        log.warning("Missing fundamental data for %s, skipping", ticker)
        return None

    # --- AlphaVantage data ---
    cf_reports = av_client.get_cash_flow(ticker)
    if not cf_reports:
        log.warning("No cash flow data for %s, skipping", ticker)
        return None

    bs_reports = av_client.get_balance_sheet(ticker)

    # --- Compute FCF metrics ---
    fcfs = compute_free_cash_flows(cf_reports, years=5)
    if len(fcfs) < 2:
        log.warning("Insufficient FCF history for %s (%d years), skipping", ticker, len(fcfs))
        return None

    avg_fcf = sum(fcfs) / len(fcfs)
    if avg_fcf <= 0:
        log.warning("Negative average FCF for %s ($%.0fM), skipping", ticker, avg_fcf / 1e6)
        return None

    growth_rate = compute_fcf_growth_rate(fcfs)

    # --- WACC ---
    wacc = estimate_wacc(info, bs_reports)

    # --- DCF ---
    ev, tv = dcf_valuation(avg_fcf, growth_rate, wacc, projection_years)

    # Net debt adjustment: EV → Equity Value
    net_debt = 0
    if bs_reports:
        latest_bs = bs_reports[0]
        total_debt = safe_float(latest_bs.get("longTermDebt")) + safe_float(latest_bs.get("shortTermDebt"))
        cash = safe_float(latest_bs.get("cashAndCashEquivalentsAtCarryingValue"))
        if cash == 0:
            cash = safe_float(latest_bs.get("cashAndShortTermInvestments"))
        net_debt = total_debt - cash

    equity_value = ev - net_debt
    dcf_per_share = equity_value / shares if shares > 0 else 0
    mos_price = dcf_per_share * (1 - margin_of_safety)
    upside = ((dcf_per_share - current_price) / current_price) * 100 if current_price > 0 else 0
    signal = classify_signal(upside, margin_of_safety)

    return StockValuation(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        market_cap=market_cap,
        current_price=current_price,
        shares_outstanding=shares,
        avg_fcf=avg_fcf,
        fcf_growth_rate=growth_rate,
        wacc=wacc,
        terminal_value=tv,
        dcf_enterprise_value=ev,
        dcf_per_share=round(dcf_per_share, 2),
        margin_of_safety_price=round(mos_price, 2),
        upside_pct=round(upside, 1),
        signal=signal,
        timestamp=datetime.now().isoformat(),
    )


def run_screen(
    tickers: list[str],
    api_key: str,
    margin_of_safety: float = DEFAULT_MARGIN_OF_SAFETY,
    projection_years: int = DEFAULT_PROJECTION_YEARS,
    max_stocks: Optional[int] = None,
) -> list[StockValuation]:
    """Screen a list of tickers and return sorted valuation results."""

    av = AlphaVantageClient(api_key)
    results = []
    total = min(len(tickers), max_stocks) if max_stocks else len(tickers)

    for i, ticker in enumerate(tickers[:total]):
        log.info("[%d/%d] %s", i + 1, total, ticker)
        try:
            val = analyze_stock(ticker, av, margin_of_safety, projection_years)
            if val:
                results.append(val)
        except Exception as e:
            log.error("Unexpected error on %s: %s", ticker, e)
            continue

    # Sort by upside (most undervalued first)
    results.sort(key=lambda v: v.upside_pct, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Output & Visualization
# ---------------------------------------------------------------------------

def results_to_dataframe(results: list[StockValuation]) -> pd.DataFrame:
    """Convert results to a clean DataFrame for export."""
    records = []
    for r in results:
        records.append({
            "Ticker": r.ticker,
            "Company": r.company_name,
            "Sector": r.sector,
            "Price": f"${r.current_price:.2f}",
            "DCF Value": f"${r.dcf_per_share:.2f}",
            "MOS Price": f"${r.margin_of_safety_price:.2f}",
            "Upside %": f"{r.upside_pct:.1f}%",
            "Signal": r.signal,
            "WACC": f"{r.wacc:.1%}",
            "FCF Growth": f"{r.fcf_growth_rate:.1%}",
            "Mkt Cap ($B)": f"${r.market_cap / 1e9:.1f}",
            "Avg FCF ($M)": f"${r.avg_fcf / 1e6:.0f}",
        })
    return pd.DataFrame(records)


def export_csv(results: list[StockValuation], filepath: str = "valuation_results.csv"):
    """Export raw valuation data to CSV."""
    df = pd.DataFrame([asdict(r) for r in results])
    df.to_csv(filepath, index=False)
    log.info("Results exported to %s", filepath)
    return filepath


def plot_valuation_chart(results: list[StockValuation], top_n: int = 20, save_path: str = "valuation_chart.png"):
    """
    Generate a horizontal bar chart comparing current price vs DCF intrinsic value
    for the top N most undervalued stocks.
    """
    top = [r for r in results if r.signal in ("BUY", "HOLD")][:top_n]
    if not top:
        log.warning("No BUY/HOLD signals to chart.")
        return None

    top.reverse()  # For horizontal bar chart (bottom = most undervalued)

    tickers = [f"{r.ticker}" for r in top]
    prices = [r.current_price for r in top]
    dcf_vals = [r.dcf_per_share for r in top]
    signals = [r.signal for r in top]

    fig, ax = plt.subplots(figsize=(12, max(6, len(top) * 0.4)))

    y_pos = range(len(tickers))
    bar_height = 0.35

    bars_price = ax.barh(
        [y - bar_height / 2 for y in y_pos], prices,
        height=bar_height, label="Current Price", color="#e74c3c", alpha=0.85
    )
    bars_dcf = ax.barh(
        [y + bar_height / 2 for y in y_pos], dcf_vals,
        height=bar_height, label="DCF Intrinsic Value", color="#2ecc71", alpha=0.85
    )

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(tickers, fontsize=9)
    ax.set_xlabel("Price per Share ($)", fontsize=11)
    ax.set_title("FortunAnalytica — Price vs. DCF Intrinsic Value", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("$%.0f"))

    # Add signal labels
    for i, r in enumerate(top):
        color = "#27ae60" if r.signal == "BUY" else "#f39c12"
        ax.annotate(
            f"  {r.signal} ({r.upside_pct:+.0f}%)",
            xy=(max(r.current_price, r.dcf_per_share), i),
            fontsize=8, fontweight="bold", color=color,
            va="center",
        )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    log.info("Chart saved to %s", save_path)
    plt.close()
    return save_path


def plot_sector_breakdown(results: list[StockValuation], save_path: str = "sector_breakdown.png"):
    """Pie chart of signal distribution by sector."""
    sector_signals = {}
    for r in results:
        if r.sector not in sector_signals:
            sector_signals[r.sector] = {"BUY": 0, "HOLD": 0, "OVERVALUED": 0}
        sector_signals[r.sector][r.signal] += 1

    sectors = list(sector_signals.keys())
    buys = [sector_signals[s]["BUY"] for s in sectors]
    holds = [sector_signals[s]["HOLD"] for s in sectors]
    overvalued = [sector_signals[s]["OVERVALUED"] for s in sectors]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(sectors))
    width = 0.25

    ax.bar([i - width for i in x], buys, width, label="BUY", color="#2ecc71")
    ax.bar(x, holds, width, label="HOLD", color="#f39c12")
    ax.bar([i + width for i in x], overvalued, width, label="OVERVALUED", color="#e74c3c")

    ax.set_xticks(list(x))
    ax.set_xticklabels(sectors, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Stock Count")
    ax.set_title("Signal Distribution by Sector", fontsize=14, fontweight="bold")
    ax.legend()

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    log.info("Sector chart saved to %s", save_path)
    plt.close()
    return save_path


def print_summary(results: list[StockValuation]):
    """Print a formatted summary table to stdout."""
    buy_count = sum(1 for r in results if r.signal == "BUY")
    hold_count = sum(1 for r in results if r.signal == "HOLD")
    over_count = sum(1 for r in results if r.signal == "OVERVALUED")

    print("\n" + "=" * 80)
    print("  FortunAnalytica — DCF Valuation Screen Results")
    print("=" * 80)
    print(f"  Stocks analyzed: {len(results)}")
    print(f"  Signals: {buy_count} BUY | {hold_count} HOLD | {over_count} OVERVALUED")
    print("-" * 80)

    df = results_to_dataframe(results)
    print(df.to_string(index=False))
    print("=" * 80 + "\n")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def load_tickers(filepath: str) -> list[str]:
    """Load ticker symbols from a CSV file."""
    try:
        df = pd.read_csv(filepath)
        col = df.columns[0]
        tickers = df[col].dropna().str.strip().tolist()
        log.info("Loaded %d tickers from %s", len(tickers), filepath)
        return tickers
    except Exception as e:
        log.error("Failed to load tickers: %s", e)
        return []


def main():
    """CLI interface for FortunAnalytica."""
    print(r"""
    ___________              __                   _____                .__          __  .__
    \_   _____/____________/  |_ __ __  ____    /  _  \   ____  ____ |  | ___.__./  |_|__| ____ _____
     |    __)/  _ \_  __ \   __\  |  \/    \  /  /_\  \ /    \/    \|  |<   |  |\   __\  |/ ___\\__  \
     |     \(  <_> )  | \/|  | |  |  /   |  \/    |    \   |  \   |  \  |_\___  | |  | |  \  \___ / __ \_
     \___  / \____/|__|   |__| |____/|___|  /\____|__  /___|  /___|  /____/ ____| |__| |__|\___  >____  /
         \/                               \/         \/     \/     \/     \/                   \/     \/
    DCF Valuation Engine v2.0
    """)

    # Configuration via CLI args or interactive input
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        api_key = input("Enter your AlphaVantage API key: ").strip()

    stock_file = "fortune500" if os.path.exists("fortune500") else None
    if len(sys.argv) > 1:
        stock_file = sys.argv[1]
    if not stock_file:
        stock_file = input("Path to stock list CSV (or press Enter for fortune500): ").strip()
        if not stock_file:
            stock_file = "fortune500"

    tickers = load_tickers(stock_file)
    if not tickers:
        log.error("No tickers loaded. Exiting.")
        return

    # Parameters
    max_stocks = int(input(f"Max stocks to analyze (default all {len(tickers)}): ").strip() or len(tickers))
    mos_input = input("Margin of Safety % (default 30): ").strip()
    margin_of_safety = float(mos_input) / 100 if mos_input else DEFAULT_MARGIN_OF_SAFETY

    # Run screen
    results = run_screen(tickers, api_key, margin_of_safety, max_stocks=max_stocks)

    if not results:
        log.warning("No valid results produced.")
        return

    # Output
    print_summary(results)
    export_csv(results)
    plot_valuation_chart(results)
    plot_sector_breakdown(results)

    print("\nOutputs saved:")
    print("  - valuation_results.csv")
    print("  - valuation_chart.png")
    print("  - sector_breakdown.png")


if __name__ == "__main__":
    main()
