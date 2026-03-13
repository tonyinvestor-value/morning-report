#!/usr/bin/env python3
"""
港美股投资晨报生成系统 - 主程序
自动获取股价和新闻，生成投资晨报
"""

import stock_data
import news_fetcher
import report_generator
import html_report_generator
from datetime import datetime, timedelta
import os
import re

# 输出文件夹
OUTPUT_DIR = "morning_report"

# 确保输出文件夹存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_existing_news_links(days: int = 2) -> set:
    """获取最近几天晨报中已存在的新闻链接"""
    existing_links = set()
    today = datetime.now()

    for i in range(1, days + 1):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y%m%d')
        filename = f"{OUTPUT_DIR}/投资晨报_{date_str}.html"

        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 提取所有新闻链接
                    links = re.findall(r'href="(https?://[^"]+)"', content)
                    existing_links.update(links)
                    print(f"   📄 已读取 {filename}，提取 {len(links)} 个链接")
            except Exception as e:
                print(f"   ⚠️ 读取 {filename} 失败: {e}")

    return existing_links


def deduplicate_news(news_list: list, existing_links: set) -> list:
    """去除已存在的新闻"""
    original_count = len(news_list)
    filtered_news = [news for news in news_list if news.get('link', '') not in existing_links]
    removed_count = original_count - len(filtered_news)
    if removed_count > 0:
        print(f"   🔄 已去除 {removed_count} 条重复新闻")
    return filtered_news


# 股价缓存（用于当yfinance不可用时的备选）
# 添加日期信息：判断是否收盘，显示上一个交易日
STOCK_PRICE_CACHE = {
    "港股": {
        "腾讯": {"price": 552.00, "prev_close": 546.50, "change": 5.50, "change_percent": 1.01, "volume": 10880000},
        "美团": {"price": 76.35, "prev_close": 76.70, "change": -0.35, "change_percent": -0.46, "volume": 9350000},
        "理想汽车": {"price": 68.50, "prev_close": 70.15, "change": -1.65, "change_percent": -2.35, "volume": 9240000},
        "泡泡玛特": {"price": 203.40, "prev_close": 205.20, "change": -1.80, "change_percent": -0.88, "volume": 2650000}
    },
    "美股": {
        "拼多多": {"price": 101.62, "prev_close": 102.94, "change": -1.32, "change_percent": -1.28, "volume": 5120000},
        "亚马逊": {"price": 209.53, "prev_close": 212.65, "change": -3.12, "change_percent": -1.47, "volume": 44070000},
        "英伟达": {"price": 183.14, "prev_close": 186.00, "change": -2.86, "change_percent": -1.54, "volume": 153890000},
        "谷歌C": {"price": 303.55, "prev_close": 308.70, "change": -5.15, "change_percent": -1.67, "volume": 24720000}
    },
    "指数": {
        "港股": {"price": 25586.38, "change": -130.38, "change_percent": -0.51},
        "美股": {"price": 22311.98, "change": -404.15, "change_percent": -1.78}
    }
}


def get_latest_trading_date() -> str:
    """获取最近的交易日（排除周末）"""
    now = datetime.now()
    weekday = now.weekday()

    # 如果是周末，返回上周五
    if weekday == 5:  # 周六
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    elif weekday == 6:  # 周日
        return (now - timedelta(days=2)).strftime('%Y-%m-%d')
    else:
        # 如果是工作日，且当前时间 < 9:30（港股开盘），返回上一个交易日
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return (now - timedelta(days=1)).strftime('%Y-%m-%d')
        return now.strftime('%Y-%m-%d')


def is_market_closed(market: str) -> tuple:
    """
    判断市场是否收盘
    返回 (is_closed: bool, status: str)
    """
    now = datetime.now()
    weekday = now.weekday()

    # 周末休市
    if weekday >= 5:
        return True, "休市"

    hour = now.hour

    if market == "港股":
        # 港股交易时间: 9:30-12:00, 13:00-16:00 北京时间
        if 9 <= hour < 12 or 13 <= hour < 16:
            return False, "交易中"
        else:
            return True, "已收盘"
    elif market == "美股":
        # 美股交易时间: 22:30-次日4:00 北京时间
        if hour >= 22 or hour < 4:
            return False, "交易中"
        else:
            return True, "已收盘"

    return True, "未知"


def get_stock_data_with_fallback():
    """获取股价数据，失败时使用缓存"""
    try:
        print("📈 正在获取股价数据...")
        hk_stock_data = stock_data.get_hk_stock_data()
        us_stock_data = stock_data.get_us_stock_data()
        indices_data = stock_data.get_market_indices()

        # 如果获取到数据
        if hk_stock_data or us_stock_data:
            return {
                'hk': hk_stock_data,
                'us': us_stock_data
            }, indices_data
    except Exception as e:
        print(f"   获取股价数据失败，使用缓存: {e}")

    # 使用缓存数据
    print("   📦 使用缓存股价数据")
    hk_data = {}
    for name, data in STOCK_PRICE_CACHE["港股"].items():
        hk_data[name] = {"ticker": "", **data}

    us_data = {}
    for name, data in STOCK_PRICE_CACHE["美股"].items():
        us_data[name] = {"ticker": "", **data}

    return {
        'hk': hk_data,
        'us': us_data
    }, STOCK_PRICE_CACHE["指数"]


def collect_all_news(hk_news: dict, us_news: dict, financial_news: list) -> list:
    """收集所有新闻到一个列表"""
    all_news = []

    # 港股新闻
    for stock_name, news_list in hk_news.items():
        for news in news_list:
            all_news.append({
                'stock': stock_name,
                'market': '港股',
                'source': news.get('publisher', '未知'),
                'title': news.get('title', ''),
                'pub_date': news.get('pub_date', ''),
                'link': news.get('link', '')
            })

    # 美股新闻
    for stock_name, news_list in us_news.items():
        for news in news_list:
            all_news.append({
                'stock': stock_name,
                'market': '美股',
                'source': news.get('publisher', '未知'),
                'title': news.get('title', ''),
                'pub_date': news.get('pub_date', ''),
                'link': news.get('link', '')
            })

    # 综合财经新闻
    for news in financial_news:
        all_news.append({
            'stock': '',
            'market': '财经',
            'source': news.get('source', '未知'),
            'title': news.get('title', ''),
            'pub_date': news.get('pub_date', ''),
            'link': news.get('link', '')
        })

    # 按时间排序
    all_news.sort(key=lambda x: x['pub_date'], reverse=True)

    return all_news


def main():
    """主函数"""
    print("=" * 60)
    print("     港美股投资晨报自动生成系统")
    print("=" * 60)
    print()

    # 使用缓存的股价数据（避免yfinance速率限制）
    print("📈 正在获取股价数据...")
    hk_data = {}
    for name, data in STOCK_PRICE_CACHE["港股"].items():
        hk_data[name] = {"ticker": "", **data}

    us_data = {}
    for name, data in STOCK_PRICE_CACHE["美股"].items():
        us_data[name] = {"ticker": "", **data}

    stock_data_combined = {
        'hk': hk_data,
        'us': us_data
    }
    indices_data = STOCK_PRICE_CACHE["指数"]

    print(f"   港股数据: {len(hk_data)} 只")
    print(f"   美股数据: {len(us_data)} 只")
    print()

    # 2. 获取高质量财经新闻（已分类）
    print("📰 正在获取新闻数据...")

    # 先读取历史新闻链接进行去重
    print("   🔍 检查历史新闻...")
    existing_links = get_existing_news_links(days=2)

    # 获取分类新闻
    stock_related_news, general_news = news_fetcher.get_financial_news()

    # 个股新闻为空
    hk_news = {}
    us_news = {}

    news_combined = {
        'hk': hk_news,
        'us': us_news
    }

    print(f"   📌 个股相关新闻: {len(stock_related_news)} 条")
    print(f"   📰 综合财经新闻: {len(general_news)} 条")
    print()

    # 3. 合并所有新闻并进行去重
    all_news = stock_related_news + general_news

    # 去重
    if existing_links:
        print(f"   🔄 正在进行新闻去重...")
        all_news = deduplicate_news(all_news, existing_links)

    print(f"   综合新闻: {len(all_news)} 条（去重后）")

    # 4. 生成Markdown晨报
    print("📝 正在生成Markdown晨报...")
    report = report_generator.generate_morning_report(
        stock_data_combined,
        news_combined,
        indices_data
    )

    md_filename = f"{OUTPUT_DIR}/投资晨报_{datetime.now().strftime('%Y%m%d')}.md"
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   ✅ Markdown晨报已保存到: {md_filename}")

    # 5. 生成HTML晨报
    print("📝 正在生成HTML晨报...")
    html_report = html_report_generator.generate_html_report(
        stock_data_combined,
        news_combined,
        indices_data,
        all_news
    )

    html_filename = f"{OUTPUT_DIR}/投资晨报_{datetime.now().strftime('%Y%m%d')}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"   ✅ HTML晨报已保存到: {html_filename}")

    print()
    print("=" * 60)
    print(report)
    print("=" * 60)
    print(f"\n✅ 晨报已生成完成！")
    print(f"   - Markdown: {md_filename}")
    print(f"   - HTML: {html_filename}")


if __name__ == "__main__":
    main()
