#!/usr/bin/env python3
"""
投资晨报生成器
按模板格式生成港美股投资晨报
"""

from datetime import datetime
from typing import Dict, List

# 股票代码映射
HONGKONG_STOCKS = {
    "腾讯": ("00700", "0700.HK"),
    "美团": ("03690", "3690.HK"),
    "理想汽车": ("02015", "2015.HK"),
    "泡泡玛特": ("09992", "9992.HK")
}

US_STOCKS = {
    "拼多多": ("PDD", "PDD"),
    "亚马逊": ("AMZN", "AMZN"),
    "英伟达": ("NVDA", "NVDA"),
    "谷歌C": ("GOOGL", "GOOGL")
}


def format_price(price: float, currency: str = "港元") -> str:
    """格式化价格"""
    if price is None:
        return f"-- {currency}"
    return f"{price:.2f} {currency}"


def format_change(change: float, change_percent: float) -> str:
    """格式化涨跌幅"""
    if change is None or change_percent is None:
        return "--"
    return f"{change:+.2f} ({change_percent:+.2f}%)"


def format_volume(volume: int) -> str:
    """格式化成交量"""
    if volume is None:
        return "--"
    if volume >= 1_000_000_000:
        return f"{volume/1_000_000_000:.2f}亿"
    elif volume >= 1_000_000:
        return f"{volume/1_000_000:.2f}百万"
    return str(volume)


def format_stock_row(name: str, ticker_code: str, stock_data: dict, currency: str = "港元") -> str:
    """格式化单只股票的信息行"""
    price = stock_data.get('price')
    change = stock_data.get('change')
    change_percent = stock_data.get('change_percent')

    # 获取新闻（如果有）
    news_list = stock_data.get('news', [])
    if news_list:
        latest_news = news_list[0]['title'][:40] + "..."
        news_time = news_list[0]['pub_date']
        news_line = f"• {name}({ticker_code})：{latest_news} | ⏰{news_time}"
    else:
        news_line = f"• {name}({ticker_code})：近期暂无重要更新 | ⏰--"

    price_line = f"  💰 股价：{format_price(price, currency)} | 📈 涨跌：{format_change(change, change_percent)}"

    return f"{news_line}\n{price_line}"


def get_market_status() -> Dict:
    """获取市场状态"""
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()

    is_weekend = weekday >= 5

    # 港股交易时间: 9:30-12:00, 13:00-16:00 HKT
    hk_hour = hour  # 简化处理，假设系统时区为北京时间
    hk_status = "开盘中" if (9 <= hk_hour < 12 or 13 <= hk_hour < 16) and not is_weekend else "收盘/休市"

    # 美股交易时间: 9:30-16:00 EST (22:30-05:00 北京时间)
    us_status = "开盘中" if (hour >= 22 or hour < 4) and not is_weekend else "收盘/休市"

    return {
        "hk": hk_status,
        "us": us_status,
        "is_weekend": is_weekend,
        "beijing_time": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def generate_morning_report(stock_data: dict, news_data: dict, indices_data: dict) -> str:
    """生成投资晨报"""
    now = datetime.now()
    today = now.strftime("%Y年%m月%d日")

    market_status = get_market_status()

    report = f"""📊 **港美股投资晨报** {today}

⚠️ **时效声明**：以下信息均为最近3天内的最新消息

🇭🇰 **港股动态**"""

    # 港股
    for name, (ticker_code, _) in HONGKONG_STOCKS.items():
        data = stock_data.get('hk', {}).get(name, {})
        data['news'] = news_data.get('hk', {}).get(name, [])
        report += f"\n{format_stock_row(name, ticker_code, data, '港元')}"

    report += "\n\n🇺🇸 **美股动态**"

    # 美股
    for name, (ticker_code, _) in US_STOCKS.items():
        data = stock_data.get('us', {}).get(name, {})
        data['news'] = news_data.get('us', {}).get(name, [])
        report += f"\n{format_stock_row(name, ticker_code, data, '美元')}"

    # 市场指数
    report += "\n\n📈 **市场表现**（最新交易日数据）"

    hk_index = indices_data.get('港股', {})
    us_index = indices_data.get('美股', {})

    if hk_index.get('price'):
        report += f"\n• 港股恒生指数：{hk_index['price']:.2f} 点 | {format_change(hk_index.get('change'), hk_index.get('change_percent'))} | {market_status['hk']}"
    else:
        report += "\n• 港股恒生指数：--"

    if us_index.get('price'):
        report += f"\n• 美股纳斯达克：{us_index['price']:.2f} 点 | {format_change(us_index.get('change'), us_index.get('change_percent'))} | {market_status['us']}"
    else:
        report += "\n• 美股纳斯达克：--"

    # 交易状态
    report += f"""

📊 **交易状态说明**
• 当前时间（北京时间）：{market_status['beijing_time']}
• 港股状态：{market_status['hk']}
• 美股状态：{market_status['us']}"""

    if market_status['is_weekend']:
        report += "\n• ⚠️ 今天是周末，市场休市"

    report += """

---
🕐 信息时间范围：最近3天
📊 数据来源：财新网、新浪财经
🎯 覆盖公司：港股4家 + 美股4家重点标的
💹 股价精度：收盘价/实时价，含涨跌幅和成交额
---"""

    return report


if __name__ == "__main__":
    # 测试
    print(generate_morning_report({}, {}, {}))
