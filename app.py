from flask import Flask, render_template, request, jsonify, send_file
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
from datetime import datetime, timedelta
import io
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint to verify yfinance is working"""
    try:
        # Try to fetch a simple stock
        test = yf.Ticker("AAPL")
        data = test.history(period="5d", auto_adjust=False)

        return jsonify({
            'status': 'healthy',
            'yfinance_version': yf.__version__,
            'test_data_rows': len(data),
            'message': 'Yahoo Finance API is accessible'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'yfinance_version': yf.__version__,
            'error': str(e),
            'message': 'Yahoo Finance API may be unavailable'
        }), 500

@app.route('/analyze', methods=['POST'])
def analyze_stock():
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()

        if not symbol:
            return jsonify({'error': 'Please provide a stock symbol'}), 400

        logger.info(f"Analyzing stock: {symbol}")

        # Fetch stock data
        stock = yf.Ticker(symbol)

        # Try multiple methods to get historical data
        hist_data = None

        # Method 1: period="1y"
        try:
            logger.info(f"Method 1: Fetching with period='1y'")
            hist_data = stock.history(period="1y", auto_adjust=False)
            logger.info(f"Method 1 result: {len(hist_data)} rows")
        except Exception as e:
            logger.error(f"Method 1 failed: {str(e)}")

        # Method 2: Try with different parameters
        if hist_data is None or hist_data.empty:
            try:
                logger.info(f"Method 2: Fetching with period='1y', interval='1d'")
                hist_data = stock.history(period="1y", interval="1d", actions=False)
                logger.info(f"Method 2 result: {len(hist_data)} rows")
            except Exception as e:
                logger.error(f"Method 2 failed: {str(e)}")

        # Method 3: Try downloading with yfinance.download
        if hist_data is None or hist_data.empty:
            try:
                logger.info(f"Method 3: Using yf.download()")
                hist_data = yf.download(symbol, period="1y", progress=False, auto_adjust=False)
                logger.info(f"Method 3 result: {len(hist_data)} rows")
            except Exception as e:
                logger.error(f"Method 3 failed: {str(e)}")

        # Method 4: Try with date range
        if hist_data is None or hist_data.empty:
            try:
                logger.info(f"Method 4: Using date range")
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                hist_data = yf.download(symbol, start=start_date, end=end_date, progress=False)
                logger.info(f"Method 4 result: {len(hist_data)} rows")
            except Exception as e:
                logger.error(f"Method 4 failed: {str(e)}")

        if hist_data is None or hist_data.empty:
            logger.error(f"All methods failed for symbol: {symbol}")
            return jsonify({'error': f'No data found for symbol: {symbol}. Please verify the symbol is correct. The Yahoo Finance API may be temporarily unavailable.'}), 404

        logger.info(f"Successfully fetched {len(hist_data)} rows of data for {symbol}")

        # Get stock info
        info = {}
        try:
            info = stock.info
            logger.info(f"Stock info fetched: {len(info)} fields")
        except Exception as e:
            logger.error(f"Failed to fetch stock info: {str(e)}")
            info = {}

        # Prepare summary data - use latest data from history if info is incomplete
        latest = hist_data.iloc[-1] if not hist_data.empty else None

        summary = {
            'symbol': symbol,
            'name': info.get('longName', info.get('shortName', symbol)),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', latest['Close'] if latest is not None else 'N/A')),
            'previous_close': info.get('previousClose', hist_data.iloc[-2]['Close'] if len(hist_data) > 1 else 'N/A'),
            'open': info.get('open', latest['Open'] if latest is not None else 'N/A'),
            'day_high': info.get('dayHigh', latest['High'] if latest is not None else 'N/A'),
            'day_low': info.get('dayLow', latest['Low'] if latest is not None else 'N/A'),
            'volume': info.get('volume', int(latest['Volume']) if latest is not None else 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            '52_week_high': info.get('fiftyTwoWeekHigh', float(hist_data['High'].max()) if not hist_data.empty else 'N/A'),
            '52_week_low': info.get('fiftyTwoWeekLow', float(hist_data['Low'].min()) if not hist_data.empty else 'N/A'),
            'avg_volume': info.get('averageVolume', int(hist_data['Volume'].mean()) if not hist_data.empty else 'N/A'),
        }

        # Prepare table data
        hist_data_reset = hist_data.reset_index()
        # Handle timezone-aware datetime
        if 'Date' in hist_data_reset.columns:
            hist_data_reset['Date'] = pd.to_datetime(hist_data_reset['Date']).dt.strftime('%Y-%m-%d')
        elif 'Datetime' in hist_data_reset.columns:
            hist_data_reset['Date'] = pd.to_datetime(hist_data_reset['Datetime']).dt.strftime('%Y-%m-%d')
        else:
            hist_data_reset['Date'] = hist_data_reset.index.strftime('%Y-%m-%d')

        table_data = hist_data_reset[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].to_dict('records')

        # Format numbers in table data
        for row in table_data:
            row['Open'] = round(row['Open'], 2)
            row['High'] = round(row['High'], 2)
            row['Low'] = round(row['Low'], 2)
            row['Close'] = round(row['Close'], 2)
            row['Volume'] = int(row['Volume'])

        # Create chart
        fig = go.Figure()

        # Add candlestick chart
        fig.add_trace(go.Candlestick(
            x=hist_data.index,
            open=hist_data['Open'],
            high=hist_data['High'],
            low=hist_data['Low'],
            close=hist_data['Close'],
            name='Price'
        ))

        # Add volume bar chart on secondary y-axis
        fig.add_trace(go.Bar(
            x=hist_data.index,
            y=hist_data['Volume'],
            name='Volume',
            yaxis='y2',
            marker=dict(color='rgba(100, 100, 250, 0.3)')
        ))

        fig.update_layout(
            title=f'{symbol} Stock Price (Last 12 Months)',
            xaxis_title='Date',
            yaxis_title='Price (USD)',
            yaxis2=dict(
                title='Volume',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            template='plotly_white',
            height=600,
            showlegend=True
        )

        chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return jsonify({
            'summary': summary,
            'table_data': table_data,
            'chart': chart_json
        })

    except Exception as e:
        return jsonify({'error': f'Error analyzing stock: {str(e)}'}), 500

@app.route('/download/<symbol>')
def download_csv(symbol):
    try:
        symbol = symbol.upper().strip()

        logger.info(f"Downloading CSV for: {symbol}")

        # Fetch stock data using multiple methods
        hist_data = None

        try:
            stock = yf.Ticker(symbol)
            hist_data = stock.history(period="1y", auto_adjust=False)
        except Exception as e:
            logger.error(f"Download method 1 failed: {str(e)}")

        if hist_data is None or hist_data.empty:
            try:
                hist_data = yf.download(symbol, period="1y", progress=False, auto_adjust=False)
            except Exception as e:
                logger.error(f"Download method 2 failed: {str(e)}")

        if hist_data is None or hist_data.empty:
            logger.error(f"Failed to download data for: {symbol}")
            return jsonify({'error': f'No data found for symbol: {symbol}'}), 404

        # Prepare CSV data
        hist_data_reset = hist_data.reset_index()
        # Handle timezone-aware datetime
        if 'Date' in hist_data_reset.columns:
            hist_data_reset['Date'] = pd.to_datetime(hist_data_reset['Date']).dt.strftime('%Y-%m-%d')
        elif 'Datetime' in hist_data_reset.columns:
            hist_data_reset['Date'] = pd.to_datetime(hist_data_reset['Datetime']).dt.strftime('%Y-%m-%d')
        else:
            hist_data_reset['Date'] = hist_data_reset.index.strftime('%Y-%m-%d')
        csv_data = hist_data_reset[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

        # Create CSV in memory
        output = io.StringIO()
        csv_data.to_csv(output, index=False)
        output.seek(0)

        # Convert to bytes
        output_bytes = io.BytesIO()
        output_bytes.write(output.getvalue().encode('utf-8'))
        output_bytes.seek(0)

        filename = f'{symbol}_stock_data_{datetime.now().strftime("%Y%m%d")}.csv'

        return send_file(
            output_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': f'Error downloading CSV: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
