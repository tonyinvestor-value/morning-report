#!/usr/bin/env python3
"""
投资晨报HTML生成器
按模板格式生成港美股投资晨报HTML
"""

from datetime import datetime, timedelta
from typing import Dict
import pytz
import os

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


def get_change_class(change_percent: float) -> str:
    """根据涨跌幅返回CSS类名"""
    if change_percent is None:
        return ""
    if change_percent > 0:
        return "positive"
    elif change_percent < 0:
        return "negative"
    return ""


def generate_stock_summary(name: str, period_data: dict) -> str:
    """生成股票多周期涨跌幅总结和预测"""
    if not period_data or name not in period_data:
        return "📊 近期暂无多周期数据"

    data = period_data.get(name, {})
    if not data:
        return "📊 近期暂无多周期数据"

    # 获取各周期数据
    data_5d = data.get("5日", {})
    data_30d = data.get("30日", {})
    data_90d = data.get("90日", {})

    change_5d = data_5d.get("change_percent")
    change_30d = data_30d.get("change_percent")
    change_90d = data_90d.get("change_percent")

    # 获取动量指标和布林带
    momentum = data.get("momentum", {})
    rsi_14 = momentum.get("rsi_14")
    momentum_30 = momentum.get("momentum_30")
    bollinger = momentum.get("bollinger")

    # 构建数据字符串
    parts = []
    if change_5d is not None:
        parts.append(f"近5日 {change_5d:+.2f}%")
    if change_30d is not None:
        parts.append(f"近30日 {change_30d:+.2f}%")
    if change_90d is not None:
        parts.append(f"近90日 {change_90d:+.2f}%")

    if not parts:
        return "📊 近期暂无多周期数据"

    # 基于动量指标生成预测（用change_5d作为短期动量）
    prediction = generate_prediction(rsi_14, change_5d, momentum_30, bollinger)

    # 生成简短总结：预测 + 数据
    result = prediction + " | " + " | ".join(parts)

    return result


def generate_prediction(rsi_14: float, change_5d: float, momentum_30: float, bollinger: dict = None) -> str:
    """基于技术指标预测未来走势 - 大白话版

    用近5日涨跌幅(change_5d)作为短期动量
    """
    if rsi_14 is None and change_5d is None:
        return "数据不足"

    # ========== 1. 短期涨跌判断（用近5日）==========
    if change_5d is not None:
        if change_5d > 5:
            trend = "最近涨得不错"
        elif change_5d > 0:
            trend = "最近小幅上涨"
        elif change_5d < -5:
            trend = "最近跌得厉害"
        elif change_5d < 0:
            trend = "最近小幅下跌"
        else:
            trend = "最近没涨没跌"
    else:
        trend = "趋势不明"

    # ========== 2. RSI信号（大白话）==========
    rsi_msg = ""
    if rsi_14 is not None:
        if rsi_14 < 30:
            rsi_msg = "价格偏低，可能要反弹"
        elif rsi_14 > 70:
            rsi_msg = "价格偏高，可能要回调"
        elif rsi_14 < 45:
            rsi_msg = "价格偏弱"
        elif rsi_14 > 55:
            rsi_msg = "价格偏强"

    # ========== 3. 布林带信号（大白话）==========
    bb_msg = ""
    if bollinger:
        if bollinger.get("squeeze"):
            bb_msg = "行情在盘整，等方向"
        elif bollinger.get("expanding"):
            if change_5d and change_5d > 0:
                bb_msg = "涨势很猛，在加速"
            elif change_5d and change_5d < 0:
                bb_msg = "跌势很猛，在加速"

        if bollinger.get("at_upper"):
            bb_msg = "快到天花板了" if not bb_msg else bb_msg + "，快到天花板了"
        elif bollinger.get("at_lower"):
            bb_msg = "快到底了" if not bb_msg else bb_msg + "，快到底了"

    # ========== 4. 拼成大白话（不要结论）==========
    parts = [trend]
    if rsi_msg:
        parts.append(rsi_msg)
    if bb_msg:
        parts.append(bb_msg)

    return "。".join(parts)


def generate_trend_summary(change_5d: float, change_30d: float, change_90d: float) -> str:
    """根据短中长期涨跌幅生成趋势总结"""
    # 简化总结
    if change_30d and change_90d:
        if change_30d > 0 and change_90d > 0:
            if change_30d > change_90d:
                return "短中期强劲，长期向好"
            else:
                return "中长期上涨，短线整理"
        elif change_30d < 0 and change_90d > 0:
            return "短期回调，中长期上升趋势未变"
        elif change_30d > 0 and change_90d < 0:
            return "短期反弹，中长期承压"
        else:
            return "短中长期均走弱"
    elif change_30d:
        if change_30d > 5:
            return "短期强势上涨"
        elif change_30d > 0:
            return "短期温和上涨"
        elif change_30d < -5:
            return "短期明显下跌"
        elif change_30d < 0:
            return "短期小幅回调"
        else:
            return "短期横盘整理"
    else:
        return "趋势不明"


def format_stock_row(name: str, ticker_code: str, stock_data: dict, currency: str = "港元", period_data: dict = None) -> str:
    """格式化单只股票的信息行"""
    price = stock_data.get('price')
    change = stock_data.get('change')
    change_percent = stock_data.get('change_percent')

    change_class = get_change_class(change_percent)

    # 生成股价总结
    summary = generate_stock_summary(name, period_data)

    # 调整顺序：先显示股价涨跌，再显示预测
    return f"""        <tr>
            <td class="stock-name">{name}({ticker_code})</td>
            <td class="price-row">
                💰 股价：{format_price(price, currency)} |
                📈 涨跌：<span class="{change_class}">{format_change(change, change_percent)}</span>
            </td>
        </tr>
        <tr>
            <td colspan="2" class="news">{summary}</td>
        </tr>"""


def get_market_status() -> Dict:
    """获取市场状态（北京时间）"""
    # 使用北京时间
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    is_weekend = weekday >= 5

    # 计算数据日期
    if is_weekend:
        # 周末返回上周五
        if weekday == 5:  # 周六
            data_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:  # 周日
            data_date = (now - timedelta(days=2)).strftime('%Y-%m-%d')
        data_date += " (周末数据)"
    else:
        # 工作日：9:30前显示上一个交易日的数据
        if hour < 9 or (hour == 9 and minute < 30):
            data_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
            data_date += " (盘前数据)"
        else:
            # 判断是否在交易时段
            if (9 <= hour < 12 or 13 <= hour < 16):  # 港股交易时段
                data_date = now.strftime('%Y-%m-%d') + " (实时)"
            else:
                data_date = now.strftime('%Y-%m-%d') + " (收盘)"

    # 港股交易时间: 9:30-12:00, 13:00-16:00 HKT
    hk_status = "开盘中" if (9 <= hour < 12 or 13 <= hour < 16) and not is_weekend else "收盘/休市"

    # 美股交易时间: 9:30-16:00 EST (22:30-05:00 北京时间)
    us_status = "开盘中" if (hour >= 22 or hour < 4) and not is_weekend else "收盘/休市"

    return {
        "hk": hk_status,
        "us": us_status,
        "is_weekend": is_weekend,
        "beijing_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "data_date": data_date
    }


def generate_html_report(stock_data: dict, news_data: dict, indices_data: dict, all_news: list = None) -> str:
    """生成HTML投资晨报"""
    now = datetime.now()
    today = now.strftime("%Y年%m月%d日")

    market_status = get_market_status()

    # 获取多周期数据
    period_data = stock_data.get('period', {})

    # 港股表格
    hk_rows = ""
    for name, (ticker_code, _) in HONGKONG_STOCKS.items():
        data = stock_data.get('hk', {}).get(name, {})
        data['news'] = news_data.get('hk', {}).get(name, [])
        hk_rows += format_stock_row(name, ticker_code, data, '港元', period_data)

    # 美股表格
    us_rows = ""
    for name, (ticker_code, _) in US_STOCKS.items():
        data = stock_data.get('us', {}).get(name, {})
        data['news'] = news_data.get('us', {}).get(name, [])
        us_rows += format_stock_row(name, ticker_code, data, '美元', period_data)

    # 市场指数
    hk_index = indices_data.get('港股', {})
    us_index = indices_data.get('美股', {})

    hk_index_html = f"{hk_index.get('price', '--'):.2f} 点 | {format_change(hk_index.get('change'), hk_index.get('change_percent'))} | {market_status['hk']}" if hk_index.get('price') else "--"
    us_index_html = f"{us_index.get('price', '--'):.2f} 点 | {format_change(us_index.get('change'), us_index.get('change_percent'))} | {market_status['us']}" if us_index.get('price') else "--"

    hk_index_class = get_change_class(hk_index.get('change_percent'))
    us_index_class = get_change_class(us_index.get('change_percent'))

    # 分类新闻列表
    # 分离个股相关新闻和综合新闻
    stock_news = []
    general_news_list = []
    for news in all_news:
        if news.get('stock'):  # 有股票标签的是个股新闻
            stock_news.append(news)
        else:
            general_news_list.append(news)

    # 个股相关新闻HTML
    stock_news_html = ""
    if stock_news:
        # 按股票分组
        stock_groups = {}
        for news in stock_news:
            stock_name = news.get('stock', '未知')
            if stock_name not in stock_groups:
                stock_groups[stock_name] = []
            stock_groups[stock_name].append(news)

        for stock_name, news_list in stock_groups.items():
            stock_news_html += f'<div class="stock-news-group"><h4>📌 {stock_name}相关新闻</h4><ul class="news-list">'
            for news in news_list[:5]:
                link = news.get('link', '')
                title = news.get('title', '暂无标题')
                source = news.get('source', '未知')
                pub_date = news.get('pub_date', '')

                if link:
                    stock_news_html += f'''            <li>
                <span class="news-source">{source}</span>
                <a href="{link}" target="_blank" class="news-title">{title}</a>
                <span class="news-time">{pub_date}</span>
            </li>'''
                else:
                    stock_news_html += f'''            <li>
                <span class="news-source">{source}</span>
                <span class="news-title">{title}</span>
                <span class="news-time">{pub_date}</span>
            </li>'''
            stock_news_html += '</ul></div>'
    else:
        stock_news_html = '<p>暂无个股相关新闻</p>'

    # 综合财经新闻HTML
    general_news_html = ""
    if general_news_list:
        for news in general_news_list[:20]:
            link = news.get('link', '')
            title = news.get('title', '暂无标题')
            source = news.get('source', '未知')
            pub_date = news.get('pub_date', '')

            if link:
                general_news_html += f'''        <li>
            <span class="news-source">{source}</span>
            <a href="{link}" target="_blank" class="news-title">{title}</a>
            <span class="news-time">{pub_date}</span>
        </li>'''
            else:
                general_news_html += f'''        <li>
            <span class="news-source">{source}</span>
            <span class="news-title">{title}</span>
            <span class="news-time">{pub_date}</span>
        </li>'''
    else:
        general_news_html = "        <li>暂无新闻</li>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>港美股投资晨报 {today}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: #1a1a2e;
            padding: 30px 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .header .date {{
            color: #666;
            font-size: 1.1em;
        }}
        .disclaimer {{
            background: #ff9800;
            color: #000;
            padding: 10px 20px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            margin-bottom: 20px;
        }}
        .section {{
            background: #ffffff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .section-title {{
            font-size: 1.4em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #1a1a2e;
        }}
        .section-title.hk {{
            color: #e53935;
        }}
        .section-title.us {{
            color: #1976d2;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .stock-name {{
            font-weight: bold;
            font-size: 1.1em;
            padding: 10px 5px;
            color: #1a1a2e;
        }}
        .news {{
            color: #666;
            font-size: 0.95em;
            padding: 8px 5px;
        }}
        .price-row {{
            padding: 10px 5px;
            color: #333;
            font-size: 0.95em;
            border-bottom: 1px solid #eee;
        }}
        .positive {{
            color: #e53935;
            font-weight: bold;
        }}
        .negative {{
            color: #43a047;
            font-weight: bold;
        }}
        .market-index {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
            margin-bottom: 10px;
        }}
        .market-index .name {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        .market-index .value {{
            font-size: 1.2em;
        }}
        .status {{
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 15px;
        }}
        .status-item {{
            flex: 1;
            min-width: 200px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }}
        .status-item .label {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .status-item .value {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        .news-list {{
            list-style: none;
        }}
        .news-list li {{
            padding: 12px 0;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .news-list li:last-child {{
            border-bottom: none;
        }}
        .news-source {{
            background: #1976d2;
            color: #fff;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            white-space: nowrap;
        }}
        .news-title {{
            flex: 1;
            color: #1976d2;
            text-decoration: none;
            cursor: pointer;
        }}
        .news-title:hover {{
            text-decoration: underline;
            color: #0d47a1;
        }}
        .news-time {{
            color: #999;
            font-size: 0.85em;
            white-space: nowrap;
        }}
        .stock-news {{
            margin-bottom: 15px;
        }}
        .stock-news-group {{
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #1976d2;
        }}
        .stock-news-group h4 {{
            margin: 0 0 10px 0;
            color: #1976d2;
            font-size: 1.1em;
        }}
        .stock-news-group .news-list {{
            margin: 0;
            padding-left: 10px;
        }}
        .strategy {{
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            margin-bottom: 10px;
        }}
        .strategy ol {{
            margin-left: 20px;
            color: #333;
        }}
        .strategy li {{
            margin-bottom: 8px;
        }}
        .footer {{
            text-align: center;
            color: #aaa;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 港美股投资晨报</h1>
            <div class="date">{today}</div>
        </div>

        <div class="disclaimer">
            ⚠️ 时效声明：以下信息均为最近3天内的最新消息
        </div>

        <div class="section">
            <h2 class="section-title hk">🇭🇰 港股动态</h2>
            <table>
                <tbody>
                    {hk_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title us">🇺🇸 美股动态</h2>
            <table>
                <tbody>
                    {us_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title">📈 市场表现</h2>
            <div class="market-index">
                <span class="name">🏢 港股恒生指数</span>
                <span class="value {hk_index_class}">{hk_index_html}</span>
            </div>
            <div class="market-index">
                <span class="name">📈 美股纳斯达克</span>
                <span class="value {us_index_class}">{us_index_html}</span>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📊 交易状态说明</h2>
            <div class="status">
                <div class="status-item">
                    <div class="label">当前时间（北京时间）</div>
                    <div class="value">{market_status['beijing_time']}</div>
                </div>
                <div class="status-item">
                    <div class="label">数据日期</div>
                    <div class="value">{market_status['data_date']}</div>
                </div>
                <div class="status-item">
                    <div class="label">港股状态</div>
                    <div class="value">{market_status['hk']}</div>
                </div>
                <div class="status-item">
                    <div class="label">美股状态</div>
                    <div class="value">{market_status['us']}</div>
                </div>
            </div>
            {"<div class='status-item' style='margin-top:10px; background:#ffebee;'><div class='label'>⚠️ 今天是周末，市场休市</div></div>" if market_status['is_weekend'] else ""}
        </div>

        <div class="section">
            <h2 class="section-title">📌 个股相关新闻</h2>
            <div class="stock-news">
                {stock_news_html}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📰 综合财经新闻</h2>
            <ul class="news-list">
                {general_news_html}
            </ul>
        </div>

        <div class="footer">
            <p>🕐 信息时间范围：最近3天</p>
            <p>📊 数据来源：财新网、新浪财经、华尔街见闻</p>
            <p>🎯 覆盖公司：港股4家 + 美股4家重点标的</p>
            <p>💹 股价精度：收盘价/实时价，含涨跌幅和成交额</p>
        </div>
    </div>
</body>
</html>"""

    return html


if __name__ == "__main__":
    # 测试
    print(generate_html_report({}, {}, {}, []))
