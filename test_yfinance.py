#!/usr/bin/env python3
"""
Simple test script to verify yfinance is working
Run: python test_yfinance.py
"""

import yfinance as yf
from datetime import datetime, timedelta

def test_yfinance():
    print("Testing yfinance with AAPL...")
    print("=" * 50)

    try:
        stock = yf.Ticker("AAPL")
        print(f"✓ Created Ticker object")

        # Test 1: history with period
        print("\nTest 1: history(period='1y', auto_adjust=False)")
        hist1 = stock.history(period="1y", auto_adjust=False)
        print(f"  Result: {len(hist1)} rows")
        if not hist1.empty:
            print(f"  Latest close: ${hist1.iloc[-1]['Close']:.2f}")

        # Test 2: yf.download
        print("\nTest 2: yf.download()")
        hist2 = yf.download("AAPL", period="5d", progress=False)
        print(f"  Result: {len(hist2)} rows")

        # Test 3: info
        print("\nTest 3: stock.info")
        info = stock.info
        print(f"  Company: {info.get('longName', 'N/A')}")
        print(f"  Price: ${info.get('currentPrice', 'N/A')}")

        print("\n" + "=" * 50)
        print("✓ All tests passed! yfinance is working.")
        print("If this works locally but fails on deployment,")
        print("the issue is likely with the hosting platform.")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nIf you see this error, yfinance might be:")
        print("  - Rate limiting your requests")
        print("  - Having temporary API issues")
        print("  - Blocked by your network/firewall")

if __name__ == "__main__":
    test_yfinance()
