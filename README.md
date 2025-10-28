# Stock Analyser

A web application to analyze stock financial data from Yahoo Finance.

## Features

- Input any stock symbol (e.g., AAPL, TSLA, GOOGL)
- View comprehensive financial data in a table format
- Interactive chart tracking stock price over time
- Download data as CSV file
- Key financial metrics and summary

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Enter a stock symbol (e.g., AAPL for Apple Inc.)
2. Click "Analyze Stock"
3. View the financial summary, data table, and interactive chart
4. Click "Download CSV" to save the data locally

## Technologies

- Python 3.x
- Flask (Web Framework)
- yfinance (Yahoo Finance API)
- Pandas (Data manipulation)
- Plotly (Interactive charts)
