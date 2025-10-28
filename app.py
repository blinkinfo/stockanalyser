from flask import Flask, render_template, request, jsonify, send_file
import yfinance as yf
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
from datetime import datetime, timedelta
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_stock():
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper().strip()

        if not symbol:
            return jsonify({'error': 'Please provide a stock symbol'}), 400

        # Fetch stock data
        stock = yf.Ticker(symbol)

        # Get historical data (1 year)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        hist_data = stock.history(start=start_date, end=end_date)

        if hist_data.empty:
            return jsonify({'error': f'No data found for symbol: {symbol}'}), 404

        # Get stock info
        info = stock.info

        # Prepare summary data
        summary = {
            'symbol': symbol,
            'name': info.get('longName', 'N/A'),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', 'N/A')),
            'previous_close': info.get('previousClose', 'N/A'),
            'open': info.get('open', 'N/A'),
            'day_high': info.get('dayHigh', 'N/A'),
            'day_low': info.get('dayLow', 'N/A'),
            'volume': info.get('volume', 'N/A'),
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            '52_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'avg_volume': info.get('averageVolume', 'N/A'),
        }

        # Prepare table data
        hist_data_reset = hist_data.reset_index()
        hist_data_reset['Date'] = hist_data_reset['Date'].dt.strftime('%Y-%m-%d')

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

        # Fetch stock data
        stock = yf.Ticker(symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        hist_data = stock.history(start=start_date, end=end_date)

        if hist_data.empty:
            return jsonify({'error': f'No data found for symbol: {symbol}'}), 404

        # Prepare CSV data
        hist_data_reset = hist_data.reset_index()
        hist_data_reset['Date'] = hist_data_reset['Date'].dt.strftime('%Y-%m-%d')
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
