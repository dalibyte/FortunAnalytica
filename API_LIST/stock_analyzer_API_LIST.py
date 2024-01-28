import requests
import yfinance as yf
import pandas as pd
import tkinter as tk
from tkinter import filedialog, ttk
import threading
import queue
import os

def get_historical_cash_flows(symbol, api_key, years=5):
    print(f"Fetching historical cash flows for {symbol}")
    url = f"https://www.alphavantage.co/query?function=CASH_FLOW&symbol={symbol}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    cash_flows = data['annualReports'][:years] if 'annualReports' in data else []
    return [cf['operatingCashflow'] for cf in cash_flows if 'operatingCashflow' in cf]

def calculate_average_cash_flow(cash_flows):
    print("Calculating average cash flow")
    cash_flows = [int(cf) for cf in cash_flows if cf]
    return sum(cash_flows) / len(cash_flows) if cash_flows else 0

def calculate_dcf(average_cash_flow, discount_rate, years):
    print("Calculating DCF")
    dcf_value = 0
    for year in range(1, years + 1):
        dcf_value += average_cash_flow / ((1 + discount_rate) ** year)
    return dcf_value

def main(gui_queue, tickers, api_keys, historical_years, projection_years, discount_rate, margin_of_safety):
    print("Main function started")
    for api_key in api_keys:
        processed_count = 0
        for ticker in tickers:
            if processed_count >= 25:
                break

            tick = yf.Ticker(ticker)
            info = tick.info
            marketcap = info.get('marketCap')

            if marketcap:
                historical_cash_flows = get_historical_cash_flows(ticker, api_key, historical_years)
                if historical_cash_flows:
                    average_cash_flow = calculate_average_cash_flow(historical_cash_flows)
                    dcf_value = calculate_dcf(average_cash_flow, discount_rate, projection_years)
                    dcf_ratio = round(dcf_value / marketcap * 100, 1)  # Rounded to the tenths place
                    result = (ticker, dcf_ratio, 'Yes' if dcf_ratio >= margin_of_safety else 'No')
                    gui_queue.put([result])
                else:
                    print(f"No cash flows data for {ticker}")

            processed_count += 1

class StockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FA Stock Analysis Tool")
        self.api_keys = []
        self.historical_years = 5
        self.projection_years = 10
        self.discount_rate = 0.1
        self.margin_of_safety = 40
        self.queue = queue.Queue()
        self.tickers = []
        self.create_widgets()

    def create_widgets(self):
        # API Key loading
        load_api_keys_button = tk.Button(self, text="Load API Keys", command=self.load_api_keys)
        load_api_keys_button.pack()

        self.api_keys_label = tk.Label(self, text="No API keys loaded.")
        self.api_keys_label.pack()

        # Stock list loading
        load_file_button = tk.Button(self, text="Load Stock List", command=self.load_stock_list)
        load_file_button.pack()

        # Margin of Safety selection
        margin_label = tk.Label(self, text="Select Margin of Safety:")
        margin_label.pack()

        margin_low_button = tk.Button(self, text="Low (20%)", command=lambda: self.set_margin_of_safety(20))
        margin_low_button.pack()

        margin_medium_button = tk.Button(self, text="Medium (40%)", command=lambda: self.set_margin_of_safety(40))
        margin_medium_button.pack()

        margin_high_button = tk.Button(self, text="High (60%)", command=lambda: self.set_margin_of_safety(60))
        margin_high_button.pack()

        self.margin_info_label = tk.Label(self, text="Higher margins reduce risk but may limit opportunities.")
        self.margin_info_label.pack()

        # Analysis button
        analyze_button = tk.Button(self, text="Analyze Stocks", command=self.start_analysis)
        analyze_button.pack()

        # Treeview for results
        self.tree = ttk.Treeview(self, columns=('Stock', 'DCF Ratio', 'Within Margin'))
        self.tree.heading('#0', text='Stock')
        self.tree.heading('#1', text='DCF Ratio')
        self.tree.heading('#2', text='Within Margin')
        self.tree.pack(expand=True, fill='both')

    def load_api_keys(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            with open(file_path, 'r') as file:
                self.api_keys = [line.strip() for line in file.readlines() if line.strip()]
            self.api_keys_label.config(text=f"{len(self.api_keys)} API keys loaded.")

    def load_stock_list(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                tickers_df = pd.read_csv(file_path, usecols=[0])
                self.tickers = tickers_df['Symbol'].dropna().tolist()
            except Exception as e:
                print(f"Error loading file: {e}")

    def set_margin_of_safety(self, margin):
        self.margin_of_safety = margin
        self.margin_info_label.config(text=f"Margin of Safety set to {margin}%. Higher margins reduce risk.")

    def start_analysis(self):
        if not self.api_keys:
            print("No API keys loaded. Please load API keys.")
            return
        if not self.tickers:
            print("No stock list loaded. Please load a stock list file.")
            return

        threading.Thread(target=main, args=(self.queue, self.tickers, self.api_keys, self.historical_years, self.projection_years, self.discount_rate, self.margin_of_safety)).start()

    def process_queue(self):
        try:
            while not self.queue.empty():
                result = self.queue.get(0)
                for stock, ratio, within_margin in result:
                    self.tree.insert('', 'end', text=stock, values=(ratio, within_margin))
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

if __name__ == "__main__":
    app = StockApp()
    app.mainloop()
