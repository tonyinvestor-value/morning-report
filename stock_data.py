#!/usr/bin/env python3
"""
港美股投资晨报生成系统
自动获取股价数据和新闻，生成投资晨报
"""

import yfinance as yf
from datetime import datetime, timedelta
import json
import time
import random

# 重点关注的股票
HONGKONG_STOCKS = {
    "腾讯": "0700.HK",
    "美团": "3690.HK",
    "理想汽车": "2015.HK",
    "泡泡玛特": "9992.HK"
}

US_STOCKS = {
    "拼多多": "PDD",
    "亚马逊": "AMZN",
    "英伟达": "NVDA",
    "谷歌C": "GOOGL"
}


def retry_get_stock_price(ticker_symbol, max_retries=5, base_delay=3):
    """带重试机制的获取股票价格"""
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker_symbol)

            # 使用 history 方法获取最近5天的数据，手动计算涨跌
            hist = stock.history(period="5d")
            volume = None

            if not hist.empty:
                # 获取最近一个有交易的日期
                closes = hist['Close'].dropna()
                if len(closes) >= 2:
                    # 最新收盘价
                    price = closes.iloc[-1]
                    # 前一天收盘价（倒数第二个）
                    prev_close = closes.iloc[-2]
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100
                    volume = hist['Volume'].iloc[-1]
                    info = {}
                elif len(closes) == 1:
                    price = closes.iloc[-1]
                    # 使用info获取前一日收盘
                    info = stock.info
                    prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose') or price
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100 if prev_close else 0
                    volume = hist['Volume'].iloc[-1]
                else:
                    price = prev_close = change = change_percent = None
                    info = {}
            else:
                # 回退到 info
                info = stock.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                if price and prev_close:
                    change = price - prev_close
                    change_percent = (change / prev_close) * 100
                else:
                    change = change_percent = None
                volume = info.get('volume')

            return {
                "price": price,
                "prev_close": prev_close,
                "change": change,
                "change_percent": change_percent,
                "volume": volume,
                "market_cap": info.get('marketCap') if 'info' in dir() else None
            }
        except Exception as e:
            error_msg = str(e)
            if "Too Many Requests" in error_msg or "Rate limited" in error_msg:
                # 速率限制，等待后重试
                delay = base_delay * (2 ** attempt) + random.uniform(0, 2)
                print(f"  ⚠️ {ticker_symbol} 速率限制，{delay:.1f}秒后重试...")
                time.sleep(delay)
                continue
            else:
                print(f"获取 {ticker_symbol} 数据失败: {e}")
                return None
    return None


def is_market_open():
    """判断当前港股和美股交易状态"""
    now = datetime.now()

    # 港股交易时间: 9:30-16:00 HKT (GMT+8)
    # 美股交易时间: 9:30-16:00 EST (GMT-5), 即 22:30-05:00 GMT+8
    hour = now.hour

    # 简单判断（实际需要考虑更多因素）
    # 港股开盘：9:30-12:00, 13:00-16:00
    hk_open = (9 <= hour < 12) or (13 <= hour < 16)

    # 美股开盘：22:30-次日4:00 (前一日晚间到次日凌晨)
    # 简化判断
    us_open = (hour >= 22) or (hour < 4)

    # 周末休市
    is_weekend = now.weekday() >= 5

    return {
        "hk": hk_open and not is_weekend,
        "us": us_open and not is_weekend,
        "is_weekend": is_weekend
    }


def get_stock_price(ticker_symbol):
    """获取股票价格数据（已弃用，使用retry_get_stock_price）"""
    return retry_get_stock_price(ticker_symbol)


def get_hk_stock_data():
    """获取港股数据"""
    results = {}
    for name, ticker in HONGKONG_STOCKS.items():
        print(f"  正在获取 {name} ({ticker})...")
        data = retry_get_stock_price(ticker)
        if data:
            results[name] = {
                "ticker": ticker,
                **data
            }
        # 添加延迟避免速率限制
        time.sleep(3 + random.uniform(0, 2))
    return results


def get_us_stock_data():
    """获取美股数据"""
    results = {}
    for name, ticker in US_STOCKS.items():
        print(f"  正在获取 {name} ({ticker})...")
        data = retry_get_stock_price(ticker)
        if data:
            results[name] = {
                "ticker": ticker,
                **data
            }
        # 添加延迟避免速率限制
        time.sleep(3 + random.uniform(0, 2))
    return results


def get_market_indices():
    """获取主要市场指数"""
    indices = {
        "港股": "^HSI",      # 恒生指数
        "美股": "^IXIC",     # 纳斯达克
        "道琼斯": "^DJI"
    }

    results = {}
    for name, ticker in indices.items():
        print(f"  正在获取 {name} 指数...")
        data = retry_get_stock_price(ticker)
        if data:
            results[name] = {
                "price": data.get('price'),
                "change": data.get('change'),
                "change_percent": data.get('change_percent')
            }
        time.sleep(1)

    return results


def main():
    """测试股价获取"""
    print("=" * 50)
    print("港美股股价数据获取测试")
    print("=" * 50)

    market_status = is_market_open()
    print(f"\n市场状态: 港股 {'开盘中' if market_status['hk'] else '收盘/休市'}, 美股 {'开盘中' if market_status['us'] else '收盘/休市'}")
    if market_status['is_weekend']:
        print("⚠️ 今天是周末")

    print("\n--- 港股数据 ---")
    hk_data = get_hk_stock_data()
    for name, data in hk_data.items():
        print(f"{name} ({data['ticker']}):")
        if data['price']:
            print(f"  当前价: {data['price']:.2f} 港元")
            print(f"  涨跌: {data['change']:+.2f} ({data['change_percent']:+.2f}%)")
        else:
            print(f"  暂无数据")

    print("\n--- 美股数据 ---")
    us_data = get_us_stock_data()
    for name, data in us_data.items():
        print(f"{name} ({data['ticker']}):")
        if data['price']:
            print(f"  当前价: ${data['price']:.2f}")
            print(f"  涨跌: ${data['change']:+.2f} ({data['change_percent']:+.2f}%)")
        else:
            print(f"  暂无数据")

    print("\n--- 市场指数 ---")
    indices = get_market_indices()
    for name, data in indices.items():
        if data['price']:
            print(f"{name}: {data['price']:.2f} ({data['change_percent']:+.2f}%)")


if __name__ == "__main__":
    main()
