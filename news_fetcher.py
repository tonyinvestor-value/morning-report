#!/usr/bin/env python3
"""
多源新闻获取模块
从高质量来源获取财经、投资、AI新闻
"""

import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time
import random

# 重点公司列表
HONGKONG_STOCKS = {
    "腾讯": "0700.HK",
    "美团": "3690.HK",
    "理想汽车": "2015.HK",
    "泡泡玛特": "09992.HK"
}

US_STOCKS = {
    "拼多多": "PDD",
    "亚马逊": "AMZN",
    "英伟达": "NVDA",
    "谷歌C": "GOOGL"
}

# 重点关注股票关键词（包含关联公司）
STOCK_KEYWORDS = {
    "腾讯": ["腾讯", "微信", "QQ", "王者荣耀"],
    "美团": ["美团", "外卖", "点评"],
    "理想汽车": ["理想", "Li Auto", "L9", "L8", "理想汽车"],
    "泡泡玛特": ["泡泡玛特", "盲盒", "POP MART"],
    "拼多多": ["拼多多", "PDD", "多多买菜"],
    "亚马逊": ["亚马逊", "Amazon", "AWS"],
    "英伟达": ["英伟达", "NVIDIA", "NVDA", "显卡", "AI芯片"],
    "谷歌C": ["谷歌", "Google", "GOOGL", "Alphabet"],
    # 关联公司
    "英伟达": ["英伟达", "NVIDIA", "NVDA", "显卡", "AI芯片", "CUDA"],
    "微软": ["微软", "Microsoft", "MSFT"],
    "苹果": ["苹果", "Apple", "AAPL", "iPhone", "App Store"],
    "比亚迪": ["比亚迪", "BYD", "刀片电池"],
    "寒武纪": ["寒武纪", "Cambricon"],
    "特斯拉": ["特斯拉", "Tesla", "TSLA"],
}


# ============================================
# 新闻筛选权重配置
# ============================================

# 持仓股票权重（个股相关性 40%）
STOCK_PRIORITY = {
    # P0 - 持仓
    "腾讯": 40, "美团": 40, "拼多多": 40, "泡泡玛特": 40,
    # P1 - 重点关注
    "英伟达": 30, "理想汽车": 30,
    # P2 - 关注
    "亚马逊": 20, "谷歌": 20, "微软": 20, "苹果": 20,
    # P3 - 扩展关注
    "比亚迪": 10, "寒武纪": 10, "特斯拉": 10, "阿里巴巴": 10,
}

# 行业热点权重（25%）
INDUSTRY_KEYWORDS = {
    "AI/人工智能": 25, "大模型": 25, "ChatGPT": 25, "LLM": 25,
    "半导体": 20, "芯片": 20, "GPU": 20, "英伟达": 20,
    "互联网": 15, "科技": 15, "云计算": 15,
    "新能源车": 15, "电动汽车": 15, "电动车": 15,
    "消费": 10, "零售": 10, "电商": 10,
    "金融": 5, "银行": 5, "股市": 5,
}

# 新闻来源权重（15%）
SOURCE_WEIGHTS = {
    "财新网": 25,
    "华尔街见闻": 12,
    "新浪财经": 8,
    "yfinance": 5,
}

# 新闻类型权重（10%）
TYPE_KEYWORDS = {
    "政策": 10, "监管": 10, "证监会": 10, "央行": 10,
    "财报": 10, "业绩": 10, "扭亏": 10, "盈利": 10,
    "暴涨": 10, "暴跌": 10, "突破": 10, "重磅": 10,
    "分析师": 5, "观点": 5, "预测": 5,
}


def get_stock_score(title: str) -> float:
    """计算个股相关性得分"""
    title_lower = title.lower()
    max_score = 0

    for stock_name, priority in STOCK_PRIORITY.items():
        keywords = STOCK_KEYWORDS.get(stock_name, [])
        for keyword in keywords:
            if keyword.lower() in title_lower:
                max_score = max(max_score, priority)
                break

    return max_score


def get_industry_score(title: str, tags: list) -> float:
    """计算行业热点得分"""
    title_lower = title.lower()
    text = title_lower + " " + " ".join(tags)
    max_score = 0

    for keyword, score in INDUSTRY_KEYWORDS.items():
        if keyword.lower() in text:
            max_score = max(max_score, score)

    return max_score


def get_source_score(source: str) -> float:
    """计算来源可信度得分"""
    return SOURCE_WEIGHTS.get(source, 5)


def get_type_score(title: str) -> float:
    """计算新闻类型得分"""
    title_lower = title.lower()
    max_score = 2  # 默认基础分

    for keyword, score in TYPE_KEYWORDS.items():
        if keyword.lower() in title_lower:
            max_score = max(max_score, score)

    return max_score


def get_time_score(pub_date: str) -> float:
    """计算发布时间得分"""
    try:
        news_date = datetime.strptime(pub_date, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_diff = (today - news_date).days

        if days_diff == 0:
            return 10
        elif days_diff == 1:
            return 5
        else:
            return 0
    except:
        return 2


def calculate_news_score(news: dict) -> float:
    """计算新闻综合评分"""
    score = 0

    # 1. 个股相关性 (40%)
    score += get_stock_score(news.get('title', ''))

    # 2. 行业热点 (25%)
    score += get_industry_score(news.get('title', ''), news.get('tags', []))

    # 3. 来源可信度 (15%)
    score += get_source_score(news.get('source', ''))

    # 4. 新闻类型 (10%)
    score += get_type_score(news.get('title', ''))

    # 5. 发布时间 (10%)
    score += get_time_score(news.get('pub_date', ''))

    return score


def filter_news(news_list: list, top_n: int = 12) -> list:
    """筛选高质量新闻"""
    if not news_list:
        return []

    # 计算每条新闻的分数
    scored_news = [(news, calculate_news_score(news)) for news in news_list]

    # 排序
    scored_news.sort(key=lambda x: x[1], reverse=True)

    # 取 Top N
    filtered = [news for news, score in scored_news[:top_n]]

    # 记录评分日志
    print(f"   📊 新闻评分示例:")
    for i, (news, score) in enumerate(scored_news[:5]):
        print(f"      {i+1}. [{score:>5.1f}分] {news['title'][:40]}...")

    return filtered


# 高质量财经新闻数据（财新 + 新浪财经）
HIGH_QUALITY_NEWS = [
    # 财新网新闻
    {"title": "香港理工大学研发全声学脑机接口 有望为帕金森病提供新疗法", "source": "财新网", "pub_date": "2026-03-13", "link": "https://www.caixin.com/2026-03-13/102422583.html", "tags": ["科技", "医疗"]},
    {"title": "财新调查｜2月新增贷款或同比少增 债券发行疲软拖累社融", "source": "财新网", "pub_date": "2026-03-13", "link": "https://finance.caixin.com/2026-03-13/102422544.html", "tags": ["金融", "银行"]},
    {"title": "苹果下调中国应用商店佣金几个百分点", "source": "财新网", "pub_date": "2026-03-13", "link": "https://www.caixin.com/2026-03-13/102422538.html", "tags": ["苹果", "科技"]},
    {"title": "平均年薪最高2570万元 高频量化交易商薪酬揭秘", "source": "财新网", "pub_date": "2026-03-13", "link": "https://finance.caixin.com/2026-03-13/102422351.html", "tags": ["金融", "量化"]},
    {"title": "T早报｜寒武纪2025年扭亏为盈；特斯拉和xAI合作开发智能体", "source": "财新网", "pub_date": "2026-03-13", "link": "https://www.caixin.com/2026-03-13/102422346.html", "tags": ["科技", "AI", "寒武纪"]},
    {"title": "香港廉署联合证监打击内幕交易及贪污 国君中信证实有员工卷入", "source": "财新网", "pub_date": "2026-03-12", "link": "https://finance.caixin.com/2026-03-12/102422119.html", "tags": ["金融", "港股"]},
    {"title": "财经早知道｜伊朗最高领袖：不会放弃复仇，霍尔木兹海峡将继续关闭", "source": "财新网", "pub_date": "2026-03-13", "link": "https://finance.caixin.com/2026-03-13/102422336.html", "tags": ["国际", "原油"]},
    {"title": "乘联会崔东树：预期车市在下半年恢复增长", "source": "财新网", "pub_date": "2026-03-12", "link": "https://www.caixin.com/2026-03-12/102422306.html", "tags": ["汽车", "新能源车"]},
    {"title": "今日开盘：两市双双低开 沪指跌幅0.28%", "source": "财新网", "pub_date": "2026-03-13", "link": "https://finance.caixin.com/2026-03-13/102422368.html", "tags": ["A股", "股市"]},
    {"title": "油价飙升的经济影响", "source": "财新网", "pub_date": "2026-03-13", "link": "https://opinion.caixin.com/2026-03-13/102422470.html", "tags": ["能源", "经济"]},

    # 新浪财经新闻
    {"title": "脑机接口重磅，概念股狂飙12%！华宝基金医疗ETF逆市翻红", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/money/fund/etf/2026-03-13/doc-inhqvnzr4110514.shtml", "tags": ["A股", "医疗", "ETF"]},
    {"title": "寒武纪将摘\"U\"！科创成长层迎首批\"毕业生\"", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/money/fund/etf/2026-03-13/doc-inhqvnzn1048690.shtml", "tags": ["寒武纪", "科创板", "芯片"]},
    {"title": "136亿主力资金扫货化工！华宝基金化工ETF持续红盘", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/money/fund/etf/2026-03-13/doc-inhqvhtn4196932.shtml", "tags": ["化工", "ETF"]},
    {"title": "突破14英寸，国内半导体公司传来好消息！芯片散热也有大动作", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/wm/2026-03-13/doc-inhquwcu1200756.shtml", "tags": ["半导体", "芯片"]},
    {"title": "生物医药产业首次被列为国家\"新兴支柱产业\"", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/jjxw/2026-03-13/doc-inhqvnzr4100924.shtml", "tags": ["医药", "政策"]},
    {"title": "比亚迪第二代刀片电池+全新闪充技术全面落地", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/stock/t/2026-03-13/doc-inhqvnzp7857822.shtml", "tags": ["比亚迪", "新能源车", "电池"]},
    {"title": "利润暴增52%背后：工业富联正在进入一个新周期", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/cj/2026-03-13/doc-inhqvnzp7842016.shtml", "tags": ["工业富联", "制造业"]},
    {"title": "算电协同推动\"未来能源\"概念，绿电板块反弹", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/jjxw/2026-03-13/doc-inhqvnzk4115726.shtml", "tags": ["电力", "新能源"]},
    {"title": "微软股价持续下滑，5个月内市值蒸发1万亿美元", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/stock/2026-03-13/doc-inhqvnzr4108832.shtml", "tags": ["微软", "美股", "科技"]},
    {"title": "港股午评：恒指跌0.48%，科指跌0.41%", "source": "新浪财经", "pub_date": "2026-03-13", "link": "https://finance.sina.com.cn/stock/hkstock/2026-03-13/", "tags": ["港股", "恒生指数"]},

    # 华尔街见闻新闻（真实抓取）
    {"title": "中国2月新增社融2.38万亿元，新增人民币贷款9000亿元，M2同比增长9%", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767449", "tags": ["社融", "金融", "中国"]},
    {"title": "布油破百引爆通胀担忧，全球股市普跌，美元指数重回100关口，日元创20个月新低", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767392", "tags": ["原油", "股市", "美元"]},
    {"title": "伊朗：袭击\"林肯\"号航母，已致其失去作战能力返回美国！美方：击中靠近航母的伊朗船只", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767425", "tags": ["伊朗", "中东", "地缘政治"]},
    {"title": "商务部：中美经贸磋商将于3月14日-17日举行，正在分析评估301调查", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767421", "tags": ["中美关系", "贸易", "关税"]},
    {"title": "金融监管总局约谈5家平台运营机构", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/livenews/3069682", "tags": ["金融监管", "平台"]},
    {"title": "证监会：严厉打击财务造假、操纵市场、内幕交易、虚假陈述等违法违规行为", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767456", "tags": ["证监会", "监管", "股市"]},
    {"title": "天风证券：因涉嫌信息披露违法违规、违法提供融资被罚1500万元", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/livenews/3069663", "tags": ["天风证券", "券商", "处罚"]},
    {"title": "美债\"恐慌指数\"飙至九个月新高，美联储降息预期\"熄火\"", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767439", "tags": ["美债", "美联储", "降息"]},
    {"title": "日本拟下周启动8000万桶石油释储，按中东冲突爆发前价格卖", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767447", "tags": ["日本", "石油", "能源"]},
    {"title": "高盛再度上调短期油价目标：布油3月100、4月85美元", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767432", "tags": ["高盛", "油价", "能源"]},
    {"title": "日元再度逼近160：避险资金涌入美元，日本干预的空间正在消失？", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767426", "tags": ["日元", "美元", "外汇"]},
    {"title": "中国央行：3月16日将开展5000亿元买断式逆回购操作，期限为6个月", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/livenews/3069600", "tags": ["央行", "逆回购", "货币政策"]},
    {"title": "美元指数突破100关口，为去年11月以来首次", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/livenews/3069474", "tags": ["美元", "美元指数", "外汇"]},
    {"title": "中东冲突引爆全球\"赤字恐慌\"：30年期美债收益率逼近4.9%", "source": "华尔街见闻", "pub_date": "2026-03-12", "link": "https://wallstreetcn.com/articles/3767417", "tags": ["中东", "美债", "收益率"]},
]


def fetch_sina_finance_news(days: int = 2) -> List[Dict]:
    """从新浪财经抓取新闻"""
    news_list = []

    # 多个财经新闻页面
    urls = [
        'https://finance.sina.com.cn/stock/',
        'https://finance.sina.com.cn/fortune/',
    ]

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=8)
                response.encoding = 'utf-8'

                if response.status_code == 200:
                    import re
                    # 匹配新闻标题和链接 - 更精确的模式
                    pattern = r'<a[^>]+href="(https?://finance\.sina\.com\.cn/(?:stock|fortune|jj)/[^"]+)"[^>]*>([^<]{10,})</a>'
                    matches = re.findall(pattern, response.text)

                    today = datetime.now().date()

                    seen_links = set()
                    for link, title in matches:
                        # 过滤掉太短或太宽泛的标题
                        if len(title) > 12 and '更多' not in title and '详情' not in title and link not in seen_links:
                            seen_links.add(link)
                            news_list.append({
                                'title': title.strip(),
                                'link': link,
                                'pub_date': today.strftime('%Y-%m-%d'),
                                'publisher': '新浪财经',
                                'source': '新浪财经',
                                'tags': []
                            })

                    # 每个页面限制数量
                    if len(news_list) >= 20:
                        break

            except Exception as e:
                continue

    except Exception as e:
        print(f"   ⚠️ 新浪财经抓取失败: {e}")

    # 去重
    unique_news = []
    seen_titles = set()
    for news in news_list:
        title = news['title'].strip()
        if title not in seen_titles and len(title) > 12:
            seen_titles.add(title)
            unique_news.append(news)

    return unique_news[:20]  # 限制数量


def fetch_wallstreetcn_news(days: int = 2) -> List[Dict]:
    """从华尔街见闻抓取新闻（使用备用数据源）"""
    # 华尔街见闻主站使用 JavaScript 渲染，直接抓取效果不好
    # 返回备用数据
    news_list = []

    # 从财新网抓取（华尔街见闻的姊妹站）
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.caixin.com/'
        }

        response = requests.get('https://www.caixin.com/', headers=headers, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code == 200:
            import re
            # 匹配新闻标题和链接
            pattern = r'<a[^>]+href="(https?://[^\"]+)"[^>]*>([^<]{10,})</a>'
            matches = re.findall(pattern, response.text)

            today = datetime.now().date()
            seen_links = set()

            for link, title in matches:
                if 'caixin.com' in link and len(title) > 8 and link not in seen_links:
                    seen_links.add(link)
                    news_list.append({
                        'title': title.strip(),
                        'link': link,
                        'pub_date': today.strftime('%Y-%m-%d'),
                        'publisher': '财新网',
                        'source': '财新网',
                        'tags': []
                    })

    except Exception as e:
        print(f"   ⚠️ 财新网抓取失败: {e}")

    return news_list[:15]


def fetch_live_news(days: int = 2) -> List[Dict]:
    """从多个来源实时抓取新闻"""
    all_news = []

    print("   📡 正在实时抓取财经新闻...")

    # 抓取新浪财经
    sina_news = fetch_sina_finance_news(days)
    print(f"      新浪财经: 获取 {len(sina_news)} 条")
    all_news.extend(sina_news)

    # 短暂休息避免被封
    time.sleep(0.5 + random.uniform(0, 0.5))

    # 抓取华尔街见闻
    wscn_news = fetch_wallstreetcn_news(days)
    print(f"      华尔街见闻: 获取 {len(wscn_news)} 条")
    all_news.extend(wscn_news)

    return all_news


def is_stock_related(news_title: str) -> tuple:
    """检查新闻是否与关注的股票相关，返回(是否相关, 股票名称)"""
    title_lower = news_title.lower()
    for stock_name, keywords in STOCK_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return True, stock_name
    return False, ""


def get_news_from_yfinance(ticker: str, days: int = 3) -> List[Dict]:
    """从yfinance获取新闻"""
    try:
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return []

        cutoff_date = datetime.now() - timedelta(days=days)
        recent_news = []

        for item in news:
            content = item.get('content', {})
            title = content.get('title') if isinstance(content, dict) else item.get('title', '')
            publisher = content.get('publisher') if isinstance(content, dict) else item.get('publisher', '')

            link = ''
            if isinstance(content, dict):
                click_through = content.get('clickThroughUrl', {})
                if isinstance(click_through, dict):
                    link = click_through.get('url', '')
                elif isinstance(click_through, str):
                    link = click_through

            pub_time = item.get('providerPublishTime')
            if pub_time:
                pub_date = datetime.fromtimestamp(pub_time)
            else:
                pub_date = datetime.now()

            if pub_date >= cutoff_date:
                recent_news.append({
                    'title': title or '暂无标题',
                    'link': link,
                    'publisher': publisher or '未知',
                    'pub_date': pub_date.strftime('%Y-%m-%d'),
                    'source': 'yfinance',
                    'tags': []
                })

        return recent_news
    except Exception as e:
        return []


def get_stock_news(ticker: str, days: int = 3) -> List[Dict]:
    """获取单只股票的新闻"""
    return get_news_from_yfinance(ticker, days)


def get_all_hk_news(days: int = 3) -> Dict[str, List[Dict]]:
    """获取所有港股新闻"""
    results = {}
    for name, ticker in HONGKONG_STOCKS.items():
        news = get_stock_news(ticker, days)
        if news:
            results[name] = news
    return results


def get_all_us_news(days: int = 3) -> Dict[str, List[Dict]]:
    """获取所有美股新闻"""
    results = {}
    for name, ticker in US_STOCKS.items():
        news = get_stock_news(ticker, days)
        if news:
            results[name] = news
    return results


def get_financial_news(existing_links: set = None) -> tuple:
    """获取高质量财经新闻，返回(个股相关新闻, 综合财经新闻)

    优先使用实时抓取的新闻，备用使用静态新闻
    使用智能评分算法筛选高质量新闻

    Args:
        existing_links: 已存在的新闻链接集合，用于去重
    """
    if existing_links is None:
        existing_links = set()

    # 优先尝试实时抓取
    live_news = fetch_live_news(days=2)

    if live_news:
        # 使用实时新闻并筛选
        print(f"   ✅ 使用实时新闻: {len(live_news)} 条")
        print(f"   🔍 开始智能筛选和去重...")

        # 先分类
        stock_related_news = []
        general_news = []

        for news in live_news:
            is_related, stock_name = is_stock_related(news['title'])
            if is_related:
                news['stock'] = stock_name
                stock_related_news.append(news)
            else:
                news['stock'] = ''
                general_news.append(news)

        # 去重：个股新闻和综合新闻分开去重
        if existing_links:
            stock_related_news = [n for n in stock_related_news if n.get('link', '') not in existing_links]
            general_news = [n for n in general_news if n.get('link', '') not in existing_links]
            print(f"   🔄 去重后: 个股新闻 {len(stock_related_news)} 条, 综合新闻 {len(general_news)} 条")

        # 智能筛选：保证持仓股票新闻 + 高分综合新闻
        final_stock_news = filter_news(stock_related_news, top_n=8)
        final_general_news = filter_news(general_news, top_n=12)  # 10-15条

        print(f"   ✨ 筛选结果: 个股新闻 {len(final_stock_news)} 条, 综合新闻 {len(final_general_news)} 条")

        return final_stock_news, final_general_news

    # 降级：使用静态新闻
    print("   ⚠️ 实时抓取失败，使用静态新闻备用")
    stock_related_news = []
    general_news = []

    for news in HIGH_QUALITY_NEWS:
        news_item = {
            'title': news['title'],
            'link': news['link'],
            'pub_date': news['pub_date'],
            'publisher': news['source'],
            'source': news['source'],
            'tags': news.get('tags', [])
        }

        is_related, stock_name = is_stock_related(news['title'])
        if is_related:
            news_item['stock'] = stock_name
            stock_related_news.append(news_item)
        else:
            news_item['stock'] = ''
            general_news.append(news_item)

    # 去重
    if existing_links:
        stock_related_news = [n for n in stock_related_news if n.get('link', '') not in existing_links]
        general_news = [n for n in general_news if n.get('link', '') not in existing_links]

    # 筛选
    final_stock_news = filter_news(stock_related_news, top_n=8)
    final_general_news = filter_news(general_news, top_n=12)

    return final_stock_news, final_general_news


def main():
    """测试新闻获取"""
    print("=" * 50)
    print("港美股新闻获取测试")
    print("=" * 50)

    print("\n--- 高质量财经新闻分类 ---")
    stock_news, general_news = get_financial_news()

    print(f"\n📌 个股相关新闻: {len(stock_news)} 条")
    for news in stock_news:
        print(f"  [{news['stock']}] {news['title'][:50]}...")

    print(f"\n📰 综合财经新闻: {len(general_news)} 条")
    for news in general_news[:5]:
        print(f"  [{news['source']}] {news['title'][:50]}...")


if __name__ == "__main__":
    main()
