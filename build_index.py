#!/usr/bin/env python3
"""Generate index.html for daily-news site (v6 Morandi minimal style)."""
import os
import re
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
import calendar

REPO_ROOT = Path(__file__).parent
ARCHIVE_DIR = REPO_ROOT / "archive"
INDEX_HTML = REPO_ROOT / "index.html"
SEARCH_JSON = REPO_ROOT / "search_index.json"

DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")

COLORS = {
    "page_bg": "#F8F6EE",
    "text_main": "#4A4640",
    "text_muted": "#A79F92",
    "line_soft": "#E3D7C7",
    "rose": "#D5A0A2",
    "sage": "#B7C0A3",
    "bluegray": "#A9BACB",
    "mustard": "#E1D39B",
    "mauve": "#C9A0B6",
    "mint": "#B3D0BF",
    "beige": "#D4B79C",
    "lavender": "#B8B0D5",
    "powder": "#A9C0DD",
    "sand": "#CFC1AA",
    "calendar_fill": "#B7BEA3",
    "calendar_ring": "#D7A1A1",
    "calendar_empty": "#D8D1C5",
    "sentiment_main": "#7F8A6A",
    "sentiment_sub": "#A59B8D",
    "grid": "#E9E0D2",
    "axis_text": "#9C9386",
}

BAR_COLORS = [
    COLORS["rose"], COLORS["sage"], COLORS["bluegray"], COLORS["mustard"],
    COLORS["mauve"], COLORS["mint"], COLORS["beige"], COLORS["lavender"],
    COLORS["powder"], COLORS["sand"],
]

# 关键词候选词表（每天扫描这些词的出现频次）
KEYWORD_LIST = [
    "英伟达", "NVIDIA", "NVDA", "AMD", "Intel", "英特尔", "台积电", "TSMC",
    "三星", "Samsung", "SK海力士", "SK Hynix", "海力士", "美光", "Micron",
    "Broadcom", "博通", "高通", "Qualcomm", "苹果", "Apple", "微软", "Microsoft",
    "谷歌", "Google", "Alphabet", "Meta", "亚马逊", "Amazon", "特斯拉", "Tesla",
    "OpenAI", "Anthropic", "Claude", "ChatGPT", "GPT", "DeepSeek", "月之暗面",
    "Kimi", "阿里", "阿里巴巴", "腾讯", "字节", "字节跳动", "华为", "小米",
    "比亚迪", "宁德时代", "中芯国际", "SMIC", "长江存储", "长鑫",
    "HBM", "HBM4", "HBM3", "DRAM", "NAND", "存储芯片", "AI芯片", "GPU",
    "算力", "数据中心", "先进制程", "2nm", "3nm", "7nm", "CoWoS", "封装",
    "美联储", "FOMC", "加息", "降息", "CPI", "PCE", "GDP", "非农",
    "油价", "Brent", "WTI", "OPEC", "黄金", "美元", "人民币", "日元",
    "特朗普", "Trump", "关税", "出口管制", "制裁", "伊朗", "以色列", "乌克兰",
    "俄罗斯", "中东", "红海", "胡塞", "朝鲜", "台湾", "台海",
    "A股", "港股", "美股", "上证", "恒生", "纳指", "标普", "道指",
    "IPO", "并购", "财报", "半年报", "年报", "营收", "净利润",
]

# 情绪判断关键词
UP_WORDS = ["涨", "大涨", "飙升", "暴涨", "涨停", "创新高", "突破", "上涨", "反弹", "利好", "回升"]
DOWN_WORDS = ["跌", "大跌", "暴跌", "崩盘", "崩跌", "重挫", "下跌", "创新低", "杀跌", "利空", "蒸发", "失守"]

# 行业分类（按每天 HTML 里的板块 emoji + 关键词）
INDUSTRY_SECTIONS = {
    "AI/芯片": ["💾", "AI", "芯片", "半导体", "HBM", "DRAM", "GPU", "算力", "存储"],
    "宏观/利率": ["📈", "美联储", "FOMC", "CPI", "PCE", "GDP", "降息", "加息", "黄金", "油价"],
    "消费": ["🛍️", "消费", "零售", "餐饮", "白酒", "家电", "奢侈品", "茶饮"],
    "新能源/汽车": ["宁德时代", "比亚迪", "特斯拉", "Tesla", "锂电", "电动车", "光伏", "储能"],
    "地缘/国际": ["🌍", "伊朗", "以色列", "乌克兰", "俄罗斯", "中东", "红海", "台海", "朝鲜"],
}


def parse_market_pct(text: str):
    """Extract main percentage move from a market h4 title. Returns float or None."""
    # Match patterns like "沪指 -1.61%" or "恒指 +0.98%" or "道指 51947 (+0.46%)"
    m = re.search(r"([+\-]\s*\d+\.\d+)%", text)
    if m:
        try:
            return float(m.group(1).replace(" ", ""))
        except ValueError:
            return None
    return None


def format_date_cn(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekdays[dt.weekday()]
    return f"{dt.year}年{dt.month}月{dt.day}日 {wd}"


def format_date_big(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekdays[dt.weekday()]
    return f"{dt.month}月{dt.day}日 · {wd}"


def extract_summary(html_path: Path, max_len: int = 90) -> str:
    try:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"<h4[^>]*>(.*?)</h4>", content, re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) > 10:
                return text[:max_len] + ("…" if len(text) > max_len else "")
        m = re.search(r"<p[^>]*>(.*?)</p>", content, re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) > 10:
                return text[:max_len] + ("…" if len(text) > max_len else "")
    except Exception:
        pass
    return "今日早报已更新"


def extract_titles(html_path: Path) -> list:
    """Extract all <h3> and <h4> title texts from a daily HTML."""
    try:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        titles = []
        for tag in ["h3", "h4"]:
            for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", content, re.DOTALL):
                text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                text = re.sub(r"\s+", " ", text)
                if 4 < len(text) < 200:
                    titles.append(text)
        return titles
    except Exception:
        return []


# 「频道词 / 板块词」黑名单——这些词是新闻板块名或常规标的代码，不算"新话题"
# （lainy 2026-08-13 澄清：Nvidia / Apple / Tesla 这种公司名是话题，板块名才是频道词）
CHANNEL_WORD_BLACKLIST = {
    # 板块/标的代码
    "A股", "港股", "美股", "韩股", "上证", "恒生", "纳指", "标普", "道指", "KOSPI",
    "沪指", "深成指", "创业板", "恒指", "恒科", "S&P", "Russell",
    "恒生科技", "恒生指数", "科创", "主板", "指数", "板块", "S&amp",
    # 宏观常规词（不是话题，是频道）
    "CPI", "PCE", "GDP", "非农", "PPI", "FOMC", "加息", "降息",
    "财报", "半年报", "年报", "营收", "净利润", "IPO", "并购",
    # 太泛的技术词
    "AI", "GPU", "CPU", "NAND", "AI芯片", "存储芯片",
    "算力", "数据中心", "先进制程", "封装", "芯片",
    # 常规主体/机构/媒体
    "特朗普", "Trump", "关税", "出口管制", "制裁", "以色列",
    "乌克兰", "俄罗斯", "中东", "红海", "胡塞", "朝鲜", "台湾", "台海",
    "Fed", "EIA", "IEA", "OPEC", "COMEX", "SEC", "FDA",
    "NYT", "CNN", "CNBC", "BBC", "FT", "WSJ", "Bloomberg", "Reuters",
    # 常见后缀/短语
    "YoY", "QoQ", "MoM", "EPS", "CEO", "CFO",
    "US", "USA", "UK", "EU", "UN", "IT",
    "Q1", "Q2", "Q3", "Q4",
    # 过泛中文词
    "今天", "明天", "昨天", "市场", "公司", "股价", "涨幅", "跌幅", "上市", "交易", "投资", "分析师",
    "中国", "美国", "韩国", "日本", "欧洲", "全球", "国际", "世界",
    "万亿", "千亿", "百亿", "亿美元", "亿元", "万元",
    "收盘", "开盘", "盘中", "早盘", "午后", "尾盘",
    "成交", "上涨", "下跌", "反弹", "回落", "涨超", "跌超",
    "新高", "新低", "纪录", "首次", "首度", "宣布", "表示", "透露", "报道", "消息", "公布", "发布",
    "同比", "环比", "预期", "实际", "数据", "显示",
}

# 话题别名归一化——同一件事物的不同叫法要合并
TOPIC_ALIAS = {
    # 公司名不同叫法
    "SK Hynix": "HBM/内存",
    "SK海力士": "HBM/内存",
    "海力士": "HBM/内存",
    "Hynix": "HBM/内存",
    "HBM": "HBM/内存",
    "HBM3": "HBM/内存",
    "HBM4": "HBM/内存",
    "HBM3E": "HBM/内存",
    "DRAM": "HBM/内存",
    "三星": "三星电子",
    "Samsung": "三星电子",
    "英伟达": "Nvidia",
    "NVIDIA": "Nvidia",
    "NVDA": "Nvidia",
    "台积电": "TSMC",
    "苹果": "Apple",
    "特斯拉": "Tesla",
    "微软": "Microsoft",
    "谷歌": "Google",
    "阿里巴巴": "阿里",
    "字节跳动": "字节",
    "Unitree": "宇树科技",
    "宇树": "宇树科技",
    "英特尔": "Intel",
    "迪士尼": "Disney",
    "月之暗面": "Kimi",
    "Anthropic": "Anthropic",
    "Claude": "Anthropic",
    "ChatGPT": "OpenAI",
    "GPT": "OpenAI",
    # 事件合并
    "Brand New Day": "Spider-Man",
    "Spider": "Spider-Man",
    "八仙": "八仙！",
    "Toy Story": "Toy Story 5",
    "Super Mario": "Super Mario Galaxy",
    "Grok Bot": "Grok",
    "Manus": "Manus AI",
    "Taalas": "AMD 收购 Taalas",
    "Terafab": "SpaceX",
    "Starlink": "SpaceX",
    "Maia": "Microsoft Maia",
    "CoWoS": "TSMC",
    "Lancium": "Nvidia",
    "Super Micro": "Super Micro",
    "SMCI": "Super Micro",
    "梁文锋": "宇树科技",
    # 宏观事件合并
    "霍尔木兹": "霍尔木兹海峡/伊朗战争",
    "霍尔木兹海峡": "霍尔木兹海峡/伊朗战争",
    "伊朗": "霍尔木兹海峡/伊朗战争",
    "伊朗战争": "霍尔木兹海峡/伊朗战争",
    "油价": "霍尔木兹海峡/伊朗战争",
    "原油": "霍尔木兹海峡/伊朗战争",
    "Brent": "霍尔木兹海峡/伊朗战争",
    "WTI": "霍尔木兹海峡/伊朗战争",
    "OPEC": "霍尔木兹海峡/伊朗战争",
    "Warsh": "美联储主席人选博弈",
    "Powell": "美联储主席人选博弈",
    "Jackson Hole": "美联储主席人选博弈",
    "美联储": "美联储主席人选博弈",
    "Shein": "Shein IPO",
}


# 太泛的中文词黑名单（这些词会出现在任何新闻标题里）
GENERIC_CN_WORDS = {
    "今天", "明天", "昨天", "市场", "公司", "股价", "涨幅", "跌幅", "上市", "交易", "投资", "分析师",
    "中国", "美国", "韩国", "日本", "欧洲", "全球", "国际", "世界",
    "万亿", "千亿", "百亿", "亿美元", "亿元", "万元",
    "收盘", "开盘", "盘中", "早盘", "午后", "尾盘",
    "科创", "创业", "主板", "指数", "板块", "个股", "股票", "基金",
    "成交", "点", "涨", "跌", "涨超", "跌超", "上涨", "下跌", "反弹", "回落",
    "新高", "新低", "记录", "纪录", "历史", "首次", "首度",
    "宣布", "表示", "透露", "报道", "消息", "公布", "发布",
    "同比", "环比", "预期", "实际", "数据", "显示",
    "成为", "进入", "推出", "发起", "推进", "启动",
}


def normalize_topic(topic: str) -> str:
    """话题别名归一化：把同一件事物的不同叫法合并。"""
    return TOPIC_ALIAS.get(topic, topic)


def extract_topics_from_title(title: str) -> list:
    """从 h4 标题里抽取「话题」事件短语。
    
    策略：
    1. 书名号《...》里的作品名
    2. 大写英文品牌/产品（带别名归一化）
    3. 中文公司+行业后缀
    4. 中文别名词典匹配
    5. 油价/霍尔木兹/伊朗 等事件主题关键词
    
    所有话题都过 CHANNEL_WORD_BLACKLIST 过滤 + TOPIC_ALIAS 归一化。"""
    topics = set()
    # 1. 书名号《...》里的作品名
    for m in re.finditer(r"《([^》]{2,20})》", title):
        topics.add(normalize_topic(m.group(1)))
    # 2. 大写英文品牌/产品
    for m in re.finditer(r"\b[A-Z][a-zA-Z0-9&-]{2,20}(?:\s+[A-Z0-9][a-zA-Z0-9&-]{0,15}){0,2}\b", title):
        phrase = m.group(0).strip()
        if phrase in CHANNEL_WORD_BLACKLIST:
            continue
        if len(phrase) < 3:
            continue
        if re.fullmatch(r"Q[1-4](\s+\d{4})?", phrase):
            continue
        if re.fullmatch(r"[A-Z]+\s*\d+", phrase):
            continue
        topics.add(normalize_topic(phrase))
    # 3. 中文公司+行业后缀（如 "宇树科技"、"百度集团"）
    for m in re.finditer(r"([一-龥]{2,4})(?:科技|集团|汽车|动漫|机器人|半导体|医药|生物|能源|银行|证券|基金|影视|娱乐|游戏|餐饮|茶饮|咖啡|美妆)", title):
        phrase = m.group(0)
        if phrase not in CHANNEL_WORD_BLACKLIST and m.group(1) not in CHANNEL_WORD_BLACKLIST:
            topics.add(normalize_topic(phrase))
    # 4. 中文别名词典匹配（重要！比如 "英伟达"、"宇树"、"特斯拉"）
    for alias in TOPIC_ALIAS:
        if re.search(r"[一-龥]", alias) and alias in title:
            topics.add(normalize_topic(alias))
    # 5. 事件主题关键词（油价/霍尔木兹/伊朗 这种没公司名但代表事件的词）
    for kw in ["霍尔木兹", "伊朗", "油价", "原油", "Brent", "WTI"]:
        if kw in title:
            topics.add(normalize_topic(kw))
            break  # 同一标题只记一次事件主题
    # 过滤
    return [t for t in topics if 2 <= len(t) <= 25 and t not in CHANNEL_WORD_BLACKLIST]


def analyze_keywords(dates: list, days: int = 30) -> tuple:
    """从 h4 标题提取「话题」并统计近 N 天被热议的天数。
    
    返回 (top10, topic_context) 元组：
    - top10: [(topic, days), ...] 按出现天数排序
    - topic_context: {topic: {"titles": [最近 3 个标题], "sentiment": "bullish/bearish/mixed"}}
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)  # 最新的在前
    topic_days = defaultdict(set)
    topic_titles = defaultdict(list)  # topic -> [(date, title), ...] 最新的在前
    for d in recent:
        html_path = ARCHIVE_DIR / f"{d}.html"
        try:
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            titles = []
            for tag in ["h3", "h4"]:
                for m in re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", content, re.DOTALL):
                    text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                    text = re.sub(r"\s+", " ", text)
                    if 4 < len(text) < 200:
                        titles.append(text)
            seen_in_doc = set()
            for title in titles:
                for topic in extract_topics_from_title(title):
                    if topic not in seen_in_doc:
                        topic_days[topic].add(d)
                        seen_in_doc.add(topic)
                        # 记录标题，取最近 3 个
                        if len(topic_titles[topic]) < 3:
                            topic_titles[topic].append((d, title))
        except Exception:
            continue
    counter = Counter({topic: len(days_set) for topic, days_set in topic_days.items()})
    # 话题必须在过去 30 天被提及 >= 3 天才算「被热议」（lainy 2026-08-13：删掉 15 天上限——持续被讨论的话题就应该一直显示）
    filtered = [(t, c) for t, c in counter.items() if c >= 3]
    top10 = sorted(filtered, key=lambda x: -x[1])[:10]
    
    # 为每个话题计算市场情绪（看涨/看跌/混合）
    topic_context = {}
    for topic, _ in top10:
        titles = [t for _, t in topic_titles.get(topic, [])]
        joined = " ".join(titles)
        up_score = sum(1 for w in UP_WORDS if w in joined)
        down_score = sum(1 for w in DOWN_WORDS if w in joined)
        if up_score > down_score and up_score >= 2:
            sentiment = "bullish"
        elif down_score > up_score and down_score >= 2:
            sentiment = "bearish"
        else:
            sentiment = "mixed"
        topic_context[topic] = {
            "titles": topic_titles.get(topic, []),
            "sentiment": sentiment,
        }
    
    return top10, topic_context


def analyze_market_sentiment(dates: list, days: int = 30):
    """Analyze each market (A股/港股/美股) by actual % moves from h4 titles.
    Returns dict: {market_key: {"up":N, "down":N, "flat":N, "avg":float, "days":N}}
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)

    market_patterns = {
        "A 股": re.compile(r"🇨🇳|A 股|沪指|上证"),
        "港股": re.compile(r"🇭🇰|港股|恒指|恒生"),
        "美股": re.compile(r"🇺🇸|美股|纳指|标普|道指|S&P"),
    }

    result = {}
    for name, pattern in market_patterns.items():
        up = down = flat = 0
        pct_sum = 0.0
        pct_count = 0
        for d in recent:
            titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
            for t in titles:
                if pattern.search(t):
                    pct = parse_market_pct(t)
                    if pct is not None:
                        pct_sum += pct
                        pct_count += 1
                        if pct >= 0.3:
                            up += 1
                        elif pct <= -0.3:
                            down += 1
                        else:
                            flat += 1
                    break  # only count first matching title per day
        avg = round(pct_sum / pct_count, 2) if pct_count > 0 else 0.0
        result[name] = {"up": up, "down": down, "flat": flat, "avg": avg, "days": pct_count}
    return result


def analyze_industry_sentiment(dates: list, days: int = 30):
    """Analyze each industry by counting up/down words in its titles.
    Returns dict: {industry: {"up":N, "down":N, "flat":N}}
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)

    result = {name: {"up": 0, "down": 0, "flat": 0} for name in INDUSTRY_SECTIONS}

    for d in recent:
        # Read whole HTML, split by section header
        try:
            content = (ARCHIVE_DIR / f"{d}.html").read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Get all h3/h4 titles in this day
        titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
        for title in titles:
            for industry, keywords in INDUSTRY_SECTIONS.items():
                if any(kw in title for kw in keywords):
                    up_score = sum(1 for w in UP_WORDS if w in title)
                    down_score = sum(1 for w in DOWN_WORDS if w in title)
                    if up_score > down_score:
                        result[industry]["up"] += 1
                    elif down_score > up_score:
                        result[industry]["down"] += 1
                    else:
                        result[industry]["flat"] += 1
                    break  # one title only counts for one industry
    return result


def analyze_sentiment(dates: list, days: int = 30):
    """Legacy overall sentiment — kept for compat. Use analyze_market_sentiment instead."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)
    up_days = down_days = flat_days = 0
    recent_events = []
    for d in recent:
        titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
        joined = " ".join(titles)
        up_score = sum(1 for w in UP_WORDS if w in joined)
        down_score = sum(1 for w in DOWN_WORDS if w in joined)
        if up_score > down_score and up_score >= 2:
            up_days += 1
        elif down_score > up_score and down_score >= 2:
            down_days += 1
        else:
            flat_days += 1
        if d >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"):
            recent_events.extend(titles[:3])
    total = up_days + down_days + flat_days
    seen = set()
    major_events = []
    for ev in recent_events:
        if ev not in seen and len(major_events) < 3:
            seen.add(ev)
            major_events.append(ev)
    return up_days, down_days, flat_days, total, major_events


# 话题上下文生成（给 TOP10 话题生成「被热议的理由」）
TOPIC_EXPLAIN = {
    "霍尔木兹海峡/伊朗战争": {
        "reason": "伊朗战争进入第 6 个月，海峡实质关闭 162+ 天，Brent 从 $83 涨到 $89，海湾国家开始绕开海峡修替代管道",
        "context": "① 伊朗提出「解除制裁才重开」+「过路费」方案被特朗普拒绝；② NYT 报道海湾国家拟投几十亿美元修替代管道；③ IEA 警告 Q3 供给缺口 180 万桶/日，全球原油库存 2017 年以来最低",
        "angle": "油价结构性高位的根本原因——战争不结束，油价不会跌，加息周期可能被推高油价打断",
        "related": "Brent 原油、沙特阿美、ADNOC、中石油/中海油、新能源车"
    },
    "Nvidia": {
        "reason": "近 30 天 18 天上头条：$5000 亿融资联盟 + 投 $30 亿给 Lancium 电力 + 拟为 OpenAI 俄亥俄数据中心担保 $2500 亿——英伟达从「卖芯片」变成「AI 基建银行」",
        "context": "① 联手 Apollo/BlackRock/KKR 等 6 大华尔街巨头建算力融资平台；② 向 Texas 电力公司 Lancium 投资 $30 亿控制电力上游；③ 为 OpenAI $5000 亿数据中心提供担保；④ 8/26 财报前市场对「AI capex 可持续性」争论不断",
        "angle": "英伟达正在把 AI 算力「金融化 + 上游锁定」，这是它应对中国廉价芯片 + 周期性风险的护城河；但也埋下「循环融资」泡沫风险",
        "related": "CoreWeave、OpenAI、Apollo、BlackRock、TSMC CoWoS"
    },
    "HBM/内存": {
        "reason": "SK Hynix + 三星 8 月前 10 天半导体出口同比 +155%，HBM 产能被锁到 2027，龙仁/清州 $380 亿扩产——AI 服务器「内存瓶颈」取代「芯片瓶颈」成为新卡点",
        "context": "① SK Hynix 8/8 批准 $380 亿扩产（龙仁 DRAM + 清州 NAND）；② 韩国 8 月前 10 天半导体出口 +155%；③ KOSPI 8/12 单日 +3.68% 触发年内第 23 次 sidecar，三星 +6%、SK Hynix +5%；④ 外资单日净买入 2 万亿韩元",
        "angle": "AI 硬件产业链的「收费站」从 GPU 转向 HBM 内存——SK Hynix 和三星的议价权被重新定价",
        "related": "SK Hynix、三星电子、Micron、味之素 ABF、KOSPI"
    },
    "三星电子": {
        "reason": "三星 Q2 业绩超预期 + HBM 出货量激增 + 韩国半导体出口 +155%——外资 8/12 单日买入 2 万亿韩元",
        "context": "① 三星 Q2 DRAM 均价环比 +30%+；② HBM3E 通过 Nvidia 验证进入量产；③ 8/12 股价单日 +6%；④ 市场押注 8 月底宣布股东回报计划（回购/分红）",
        "angle": "三星从「追赶 SK Hynix」变成「AI 内存双寡头」之一，估值重估期",
        "related": "SK Hynix、HBM、KOSPI、Nvidia"
    },
    "AMD": {
        "reason": "AMD 8/10 收购 AI 推理芯片创企 Taalas + 与 Intel/Nvidia 8/12 集体上涨——AMD 从「训练侧追赶者」转向「推理侧颠覆者」",
        "context": "① 收购 Taalas 把 AI 模型「刻进」硅片，推理性能 10 倍提升；② 8/12 Super Micro 财报后 AMD/Intel/Nvidia 集体上涨，AI 服务器供应链重新联动；③ MI400 系列被 OpenAI 采用",
        "angle": "AI 芯片战场从「训练」转向「推理」——AMD 在推理侧的性价比优势被放大",
        "related": "Taalas、Super Micro、Intel、Nvidia、OpenAI"
    },
    "TSMC": {
        "reason": "CoWoS 5.5-reticle 良率达 99% + 14-reticle 版 2028 量产 + Microsoft 求 30 万片 Maia 300 产能——TSMC 先进封装成 AI 新「收费站」",
        "context": "① 7 月营收 NT$4676 亿（$14.5B）同比 +44.7%；② CoWoS 产能近三年每年翻倍，10 座先进封装厂；③ Nvidia 独占 60% CoWoS 队列，前三名客户占 85%+；④ 排队周期 52-78 周",
        "angle": "CoWoS 是 AI 产业链的「真·瓶颈」——比芯片本身更难扩产，TSMC 议价权短期不可挑战",
        "related": "CoWoS、Nvidia、Microsoft、Broadcom、AMD、ABF 基板"
    },
    "Intel": {
        "reason": "Intel $200 亿增发 8/12 收盘：$95/股，$1000 亿订单涌入（5 倍超额），Dan Niles 预告「大代工客户将官宣」",
        "context": "① 增发规模从 $150 亿上调至 $200 亿；② 机构需求 $1000 亿说明不是「救」而是「赌」；③ 18A 工艺被传可能拿下 Nvidia/Apple 订单；④ 但股价 8/11 跌 -1.5%，市场担忧 15-20% 稀释",
        "angle": "Intel 18A 翻身的最后一搏——如果真签下大代工客户，股价有重估空间；否则就是缓慢的衰落",
        "related": "Nvidia、Apple、TSMC、Dan Niles"
    },
    "功夫女足": {
        "reason": "暑期档国产体育片黑马：票房近 22 亿，连续多天单日票房榜首，女性观众占比高",
        "context": "① 2026 暑期档总票房破 86 亿创纪录；② 《功夫女足》从首日 1.2 亿逆袭到 22 亿，豆瓣评分 8.3；③ 国产体育片首次突破 20 亿量级；④ 社交媒体话题发酵",
        "angle": "中国电影复苏的最强信号——观众不是不进影院，而是要「值得大银幕」的内容",
        "related": "八仙！、Toy Story 5、Spider-Man、暑期档票房"
    },
    "Spider-Man": {
        "reason": "《Spider-Man: Brand New Day》开画 6 天破 $10 亿创影史第二快纪录，Disney CEO 财报电话会公开点赞",
        "context": "① 上映 65 年后 Spider-Man 仍是超级英雄最强 IP；② 索尼+漫威共享版权模式持续验证；③ 2026 暑期档全球票房创纪录；④ Toy Story 5 以 $4.61 亿领跑",
        "angle": "超级英雄 IP 的「长青化」——Sony 和 Disney 双受益，衍生品收入是长期金矿",
        "related": "Sony、Disney、Marvel、Brand New Day"
    },
    "美联储主席人选博弈": {
        "reason": "Kevin Warsh 成为下任美联储主席最热门人选，8/7 公开表态「准备好加息」——市场重新定价 2026 年货币政策路径",
        "context": "① 特朗普多次暗示要换 Powell；② Warsh 作为前 Fed 理事 + 尖锐批评者被市场视为「鹰派」；③ 8/7 公开表态「若通胀偏热将采取行动」；④ FOMC 7/29 投票 9-3，三名官员异议支持加息",
        "angle": "如果 Warsh 接任，加息周期可能重启——这对新兴市场、AI 估值、黄金都是关键变量",
        "related": "Powell、Trump、FOMC、CPI、美债 10Y"
    },
    "宇树科技": {
        "reason": "A 股人形机器人第一股 IPO：超额认购 8000 倍创科创板纪录，散户 978 万户抢购，中签率 0.018% 创历史新低",
        "context": "① 定价 150.80 元/股，市值 610 亿，219 倍 PE；② 梁文锋通过 DeepSeek 战略配售 + 幻方量化网下打新获配 119 万股；③ 黄牛收购价 410 元/股（比发行价高 170%）；④ 8/13 上市首日",
        "angle": "A 股对人形机器人赛道的「信仰级」定价——参考 2015 年创业板泡沫，但宇树有真实量产能力（Go2 机器狗全球销售）",
        "related": "DeepSeek、梁文锋、A 股、科创板、人形机器人"
    },
    "SpaceX": {
        "reason": "SpaceX + Tesla 联合建 $168 亿 Terafab 芯片厂 + Starlink 收入爆发 + Grok Bot 发布——马斯克生态闭环成型",
        "context": "① 8/10 宣布 $168 亿 Terafab 落地德州，1 亿平方英尺垂直整合；② Intel/xAI 合资，瞄准先进制程；③ SpaceXAI 8/12 发布 Grok Bot 企业级 AI Agent，缩小与 OpenAI 差距",
        "angle": "SpaceX 从「火箭公司」变成「太空+芯片+AI+通信」综合平台——估值逻辑彻底重写",
        "related": "Tesla、xAI、Intel、Starlink、Grok"
    },
    "Apple": {
        "reason": "Tim Cook 任内最后一份财报被「内存短缺」打场，股价单日暴跌近 10%；同时 H1 在中国市场双位数增长——供需两侧同受压缩",
        "context": "① 8/1 苹果财报后股价暴跌近 10%，主因是内存（DRAM/NAND）短缺导致 iPhone 供货紧张；② H1 在中国市场双位数增长，与可乐/阿迪/欧莱菊同时上榜「跨国巨头逆势增长」；③ 分析师担心 AI 服务器抢购内存会推高 iPhone 成本；④ Tim Cook 即将交棒，接班人问题公开化",
        "angle": "Apple 正在面临「AI 内存抢资源」与「领导层交替」双重不确定性——短期压力但长期品牌护城河仍在",
        "related": "SK Hynix、Micron、DRAM、Tim Cook、iPhone"
    },
}

SENTIMENT_LABEL = {
    "bullish": ("📈", "市场偏多"),
    "bearish": ("📉", "市场偏空"),
    "mixed": ("⚖️", "多空混合"),
}

def render_bar_chart(top10: list, topic_context: dict = None) -> str:
    """Render vertical bar chart with 10 morandi colors + clickable topic cards."""
    if not top10:
        return ""
    max_count = top10[0][1] if top10 else 1
    bars_html = []
    for i, (kw, count) in enumerate(top10):
        height_pct = int(count / max_count * 100)
        color = BAR_COLORS[i % len(BAR_COLORS)]
        bars_html.append(f'''
        <div class="bar-item">
          <div class="bar-value">{count}</div>
          <div class="bar-track">
            <div class="bar-fill" style="height:{height_pct}%; background:{color};"></div>
          </div>
          <div class="bar-label">{kw}</div>
        </div>''')
    
    # 生成可点击的话题卡片
    cards_html = []
    topic_context = topic_context or {}
    for i, (kw, count) in enumerate(top10):
        color = BAR_COLORS[i % len(BAR_COLORS)]
        ctx = topic_context.get(kw, {})
        sentiment_key = ctx.get("sentiment", "mixed")
        sentiment_emoji, sentiment_label = SENTIMENT_LABEL.get(sentiment_key, SENTIMENT_LABEL["mixed"])
        
        # 最近标题样本
        titles = ctx.get("titles", [])
        titles_html = ""
        if titles:
            titles_html = "<ul class='topic-titles'>" + "".join(
                f"<li><span class='topic-date'>{d}</span> {t}</li>" for d, t in titles[:3]
            ) + "</ul>"
        
        # 手写解释（如果有）
        explain = TOPIC_EXPLAIN.get(kw, {})
        reason = explain.get("reason", "")
        context_txt = explain.get("context", "")
        angle = explain.get("angle", "")
        related = explain.get("related", "")
        
        explain_html = ""
        if reason:
            explain_html += f"<div class='topic-reason'><strong>🔥 为什么被热议：</strong>{reason}</div>"
        if context_txt:
            explain_html += f"<div class='topic-context'><strong>📖 背景：</strong>{context_txt}</div>"
        if angle:
            explain_html += f"<div class='topic-angle'><strong>🎯 视角：</strong>{angle}</div>"
        if related:
            explain_html += f"<div class='topic-related'><strong>🔗 关联话题：</strong>{related}</div>"
        if not explain_html and titles_html:
            explain_html = f"<div class='topic-context'><strong>📖 近期报道：</strong></div>{titles_html}"
        elif explain_html and titles_html:
            explain_html += f"<div class='topic-context' style='margin-top:10px'><strong>📰 近期相关标题：</strong></div>{titles_html}"
        
        cards_html.append(f'''
        <details class="topic-card" style="border-left-color:{color}">
          <summary>
            <span class="topic-rank" style="background:{color}">#{i+1}</span>
            <span class="topic-name">{kw}</span>
            <span class="topic-meta">
              <span class="topic-days">{count} 天被提及</span>
              <span class="topic-sentiment">{sentiment_emoji} {sentiment_label}</span>
            </span>
            <span class="topic-toggle">▼</span>
          </summary>
          <div class="topic-detail">
            {explain_html}
          </div>
        </details>''')
    
    return f'''<div class="bar-chart">{"".join(bars_html)}</div>
<div class="topic-cards">
  <div class="topic-cards-hint">👇 点击话题展开「为什么被热议」</div>
  {"".join(cards_html)}
</div>'''


def build_calendar_html(dates_set: set, today_str: str) -> str:
    if not dates_set:
        return ""
    by_month = defaultdict(set)
    for d in dates_set:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        by_month[(dt.year, dt.month)].add(dt.day)

    sorted_months = sorted(by_month.keys(), reverse=True)
    sorted_months = sorted(sorted_months)

    today = datetime.strptime(today_str, "%Y-%m-%d").date() if today_str else None

    month_blocks = []
    for (y, m) in sorted_months:
        cal = calendar.monthcalendar(y, m)
        active_days = by_month[(y, m)]

        rows_html = []
        rows_html.append('<div class="cal-row cal-header">' + ''.join(f'<span>{d}</span>' for d in ["一","二","三","四","五","六","日"]) + '</div>')

        for week in cal:
            cells = []
            for day in week:
                if day == 0:
                    cells.append('<span class="cal-day empty"></span>')
                else:
                    date_obj = date(y, m, day)
                    is_active = day in active_days
                    is_today = (today and date_obj == today)
                    classes = ["cal-day"]
                    if is_active:
                        classes.append("active")
                    if is_today:
                        classes.append("today")
                    cls = " ".join(classes)
                    if is_active:
                        link = f"archive/{y:04d}-{m:02d}-{day:02d}.html"
                        cells.append(f'<a class="{cls}" href="{link}">{day}</a>')
                    else:
                        cells.append(f'<span class="{cls}">{day}</span>')
            rows_html.append('<div class="cal-row">' + ''.join(cells) + '</div>')

        month_title = f"{m}月"
        month_blocks.append(f'''
        <div class="cal-month">
          <div class="cal-month-title">{month_title}</div>
          {''.join(rows_html)}
        </div>''')

    return f'<div class="cal-grid">{"".join(month_blocks)}</div>'


def build_weekly_highlights(dates: list, days: int = 7) -> str:
    """本周大事记：从近 N 天早报中挑出影响力最大的 5-8 条事件，跨天去重。"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)
    if not recent:
        return ""
    # 收集每天所有标题
    all_entries = []  # [(date, title)] 
    for d in recent:
        titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
        for t in titles:
            all_entries.append((d, t))
    # 按「事件主体」去重：同主体只留最近 + 最重要的一条
    seen_subjects = {}
    KEYWORD_IMPORTANCE = ["纪录", "创", "首次", "首", "爆发", "暴涨", "飙升", "突破", "落地", "收购", "签署", "发布", "IPO", "紧急", "宣布", "爆表", "超预期", "签署"]
    for d, t in all_entries:
        # 抽主体关键词（优先别名）
        subj = None
        for alias in TOPIC_ALIAS:
            if alias in t:
                subj = normalize_topic(alias)
                break
        if not subj:
            m = re.search(r"\b[A-Z][a-zA-Z0-9&-]{2,15}\b", t)
            if m:
                subj = normalize_topic(m.group(0))
        if not subj:
            # 中文主体（人名/公司名）
            m = re.search(r"([一-龥]{2,4})(?:科技|集团|汽车|机器人|半导体|医药|银行|证券|影视|娱乐|游戏)", t)
            if m:
                subj = m.group(0)
        if not subj:
            continue
        # 计算重要性分数
        score = sum(2 for kw in KEYWORD_IMPORTANCE if kw in t) + len(re.findall(r"\d+%|\$\d+|\d+\s*亿", t))
        if subj not in seen_subjects or score > seen_subjects[subj][0] or d > seen_subjects[subj][1]:
            # 同主体：如果分数更高 或 是更新日期的，替换
            if subj not in seen_subjects:
                seen_subjects[subj] = (score, d, t)
            elif score > seen_subjects[subj][0]:
                seen_subjects[subj] = (score, d, t)
    # 按日期倒序 + 重要性排序
    items = sorted(seen_subjects.values(), key=lambda x: x[1], reverse=True)[:8]  # 取最近 8 条不同主体的
    if not items:
        return ""
    lis = "".join(
        f'<li><span class="hl-date">{d[5:].replace("-", "/")}</span> <a href="archive/{d}.html">{t}</a></li>'
        for _, d, t in items
    )
    return f'''
  <div class="weekly-section">
    <div class="section-title">📅 本周大事记（近 {days} 天）</div>
    <ul class="weekly-list">{lis}</ul>
  </div>'''


def build_geo_timeline(dates: list, topic: str, days: int = 30) -> str:
    """地缘事件时间轴：某个持续事件在近 N 天里的演进。"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff])
    entries = []
    # 该事件相关的所有话题别名
    related_aliases = [a for a, n in TOPIC_ALIAS.items() if n == topic] + [topic]
    for d in recent:
        titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
        for t in titles:
            if any(a in t for a in related_aliases):
                entries.append((d, t))
                break  # 一天一条代表
    if len(entries) < 2:
        return ""
    lis = "".join(
        f'<li><span class="hl-date">{d[5:].replace("-", "/")}</span> <a href="archive/{d}.html">{t}</a></li>'
        for d, t in entries
    )
    return f'''
  <div class="geo-section">
    <div class="section-title">🌍 「{topic}」事件演进时间轴（近 {days} 天）</div>
    <ul class="weekly-list">{lis}</ul>
  </div>'''


def build_search_index(dates: list) -> str:
    """全站搜索：生成 search_index.json（搜索框已嵌在顶栏）。"""
    index = []
    for d in sorted(dates, reverse=True)[:90]:  # 最近 90 天
        titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
        index.append({"date": d, "titles": titles})
    SEARCH_JSON.parent.mkdir(exist_ok=True)
    SEARCH_JSON.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return ""


def build_topic_reverse_index(top10: list, dates: list, days: int = 30) -> str:
    """话题反向索引：点击话题看过去 N 天所有相关标题。"""
    if not top10:
        return ""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = sorted([d for d in dates if d >= cutoff], reverse=True)
    blocks = []
    for topic, _count in top10:
        related_aliases = [a for a, n in TOPIC_ALIAS.items() if n == topic] + [topic]
        entries = []
        for d in recent:
            titles = extract_titles(ARCHIVE_DIR / f"{d}.html")
            for t in titles:
                if any(a in t for a in related_aliases):
                    entries.append((d, t))
        if not entries:
            continue
        lis = "".join(
            f'<li><span class="hl-date">{d[5:].replace("-", "/")}</span> <a href="archive/{d}.html">{t}</a></li>'
            for d, t in entries
        )
        blocks.append(f'''
      <details class="topic-reverse">
        <summary><strong>{topic}</strong> · {len(entries)} 条相关报道</summary>
        <ul class="weekly-list">{lis}</ul>
      </details>''')
    if not blocks:
        return ""
    return f'''
  <div class="topic-reverse-section">
    <div class="section-title">🔗 话题反向索引（点击查看完整演进）</div>
    {"".join(blocks)}
  </div>'''


def main():
    dates = []
    for f in ARCHIVE_DIR.iterdir():
        m = DATE_PATTERN.match(f.name)
        if m:
            dates.append(m.group(1))
    dates.sort(reverse=True)

    latest = dates[0] if dates else None
    total = len(dates)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    summary = ""
    if latest:
        summary = extract_summary(ARCHIVE_DIR / f"{latest}.html")

    dates_set = set(dates)
    calendar_html = build_calendar_html(dates_set, latest)

    # 近 30 天数据分析
    top10, topic_context = analyze_keywords(dates, days=30)
    bar_chart_html = render_bar_chart(top10, topic_context)
    up_days, down_days, flat_days, sentiment_total, major_events = analyze_sentiment(dates, days=30)
    market_sent = analyze_market_sentiment(dates, days=30)
    industry_sent = analyze_industry_sentiment(dates, days=30)

    # 新增：本周大事记 + 话题反向索引 + 全站搜索 + 地缘事件时间轴
    weekly_html = build_weekly_highlights(dates, days=7)
    topic_reverse_html = build_topic_reverse_index(top10, dates, days=30)
    build_search_index(dates)  # 生成 search_index.json（搜索框在顶栏）
    geo_html = build_geo_timeline(dates, "霍尔木兹海峡/伊朗战争", days=30)

    # 主要事件（近 7 天）
    events_html = ""
    if major_events:
        events_str = "；".join(major_events)
        events_html = f'<div class="sentiment-events">近期主要事件：{events_str}</div>'

    # 按市场渲染
    def render_market_block(name: str, data: dict) -> str:
        up, down, flat, avg, days = data["up"], data["down"], data["flat"], data["avg"], data["days"]
        if days == 0:
            return ""
        if up > down:
            label = "📈 偏乐观"
            color = "#B7C0A3"
        elif down > up:
            label = "📉 偏悲观"
            color = "#D5A0A2"
        else:
            label = "➖ 震荡"
            color = "#A9BACB"
        avg_str = f"{avg:+.2f}%" if avg != 0 else "0%"
        return f'''
        <div class="market-block">
          <div class="market-name" style="border-left-color:{color};">{name}</div>
          <div class="market-data">
            <span class="market-label">{label}</span>
            <span class="market-avg">平均 {avg_str}</span>
          </div>
          <div class="market-detail">涨 {up} 天 · 跌 {down} 天 · 震荡 {flat} 天</div>
        </div>'''

    market_blocks = "".join(render_market_block(name, data) for name, data in market_sent.items())

    # 按行业渲染
    def render_industry_block(name: str, data: dict) -> str:
        up, down, flat = data["up"], data["down"], data["flat"]
        total = up + down + flat
        if total == 0:
            return ""
        if up > down:
            label = "📈"
            color = "#B7C0A3"
        elif down > up:
            label = "📉"
            color = "#D5A0A2"
        else:
            label = "➖"
            color = "#A9BACB"
        return f'''
        <div class="industry-item">
          <span class="industry-icon" style="background:{color};">{label}</span>
          <span class="industry-name">{name}</span>
          <span class="industry-detail">↑{up} ↓{down} −{flat}</span>
        </div>'''

    industry_items = "".join(render_industry_block(name, data) for name, data in industry_sent.items())

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦞 龙虾老师 · 每日不错过新闻</title>
<style>
  :root {{
    --page-bg: {COLORS["page_bg"]};
    --text-main: {COLORS["text_main"]};
    --text-muted: {COLORS["text_muted"]};
    --line-soft: {COLORS["line_soft"]};
    --rose: {COLORS["rose"]};
    --sage: {COLORS["sage"]};
    --calendar-fill: {COLORS["calendar_fill"]};
    --calendar-ring: {COLORS["calendar_ring"]};
    --calendar-empty: {COLORS["calendar_empty"]};
    --sentiment-main: {COLORS["sentiment_main"]};
    --sentiment-sub: {COLORS["sentiment_sub"]};
    --grid: {COLORS["grid"]};
    --axis-text: {COLORS["axis_text"]};
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--page-bg);
    color: var(--text-main);
    min-height: 100vh;
    padding: 40px 20px;
  }}
  .container {{
    max-width: 760px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    padding-bottom: 24px;
    border-bottom: 1px solid var(--line-soft);
    margin-bottom: 40px;
  }}
  h1 {{
    font-size: 24px;
    color: var(--text-main);
    margin-bottom: 6px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }}
  .subtitle {{
    color: var(--text-muted);
    font-size: 13px;
    letter-spacing: 1px;
  }}
  .today-section {{
    text-align: center;
    margin-bottom: 48px;
  }}
  .today-label {{
    color: var(--text-muted);
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 12px;
  }}
  .today-date {{
    font-size: 42px;
    color: var(--text-main);
    font-weight: 600;
    margin-bottom: 16px;
    font-family: Georgia, "PingFang SC", serif;
  }}
  .today-date a {{
    color: var(--text-main);
    text-decoration: none;
    border-bottom: 2px solid var(--rose);
    transition: color 0.15s;
  }}
  .today-date a:hover {{
    color: var(--rose);
  }}
  .today-summary {{
    color: var(--text-muted);
    font-size: 14px;
    line-height: 1.7;
    max-width: 480px;
    margin: 0 auto;
  }}
  .section-title {{
    color: var(--text-muted);
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 20px;
    text-align: center;
  }}

  /* Insights section (TOP10 + sentiment) */
  .insights-section {{
    margin: 32px 0 48px;
  }}
  .bar-chart {{
    display: flex;
    align-items: flex-end;
    justify-content: space-around;
    gap: 8px;
    height: 220px;
    padding: 16px 8px 0;
    border-bottom: 1px solid var(--grid);
    margin-bottom: 8px;
  }}
  .bar-item {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    height: 100%;
    max-width: 60px;
  }}
  .bar-value {{
    color: var(--text-main);
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 4px;
  }}
  .bar-track {{
    flex: 1;
    width: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    position: relative;
  }}
  .bar-fill {{
    width: 100%;
    border-radius: 4px 4px 0 0;
    transition: opacity 0.15s;
  }}
  .bar-fill:hover {{
    opacity: 0.85;
  }}
  .bar-label {{
    color: var(--axis-text);
    font-size: 11px;
    margin-top: 8px;
    transform: rotate(-30deg);
    transform-origin: center;
    white-space: nowrap;
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  /* 话题卡片（点击展开） */
  .topic-cards {{
    margin-top: 20px;
  }}
  .topic-cards-hint {{
    text-align: center;
    color: var(--text-dim);
    font-size: 12px;
    margin-bottom: 12px;
  }}
  .topic-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
    transition: background 0.15s;
  }}
  .topic-card summary {{
    padding: 12px 16px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    list-style: none;
    user-select: none;
  }}
  .topic-card summary::-webkit-details-marker {{
    display: none;
  }}
  .topic-card summary:hover {{
    background: var(--card-hover, #f8f6f2);
  }}
  .topic-card[open] summary {{
    border-bottom: 1px solid var(--border);
  }}
  .topic-card[open] .topic-toggle {{
    transform: rotate(180deg);
  }}
  .topic-rank {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 22px;
    padding: 0 6px;
    border-radius: 4px;
    color: white;
    font-size: 11px;
    font-weight: 600;
  }}
  .topic-name {{
    font-weight: 600;
    font-size: 14px;
    color: var(--text-main);
  }}
  .topic-meta {{
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
    color: var(--text-dim);
  }}
  .topic-sentiment {{
    font-weight: 500;
  }}
  .topic-toggle {{
    color: var(--text-dim);
    font-size: 11px;
    transition: transform 0.2s;
  }}
  .topic-detail {{
    padding: 14px 18px;
    font-size: 13px;
    line-height: 1.7;
    color: var(--text-main);
  }}
  .topic-detail .topic-reason {{
    margin-bottom: 8px;
  }}
  .topic-detail .topic-context {{
    margin-bottom: 8px;
    color: var(--text-dim);
  }}
  .topic-detail .topic-angle {{
    color: var(--accent);
    font-style: italic;
  }}
  .topic-detail .topic-related {{
    margin-top: 8px;
    font-size: 12px;
    color: var(--text-dim);
  }}
  .topic-detail .topic-titles {{
    margin: 4px 0 0;
    padding-left: 18px;
    color: var(--text-dim);
    font-size: 12px;
  }}
  .topic-detail .topic-titles li {{
    margin: 2px 0;
  }}
  .topic-detail .topic-date {{
    color: var(--accent);
    font-weight: 500;
    margin-right: 6px;
  }}
  .chart-caption {{
    text-align: center;
    color: var(--text-muted);
    font-size: 11px;
    margin-top: 24px;
    letter-spacing: 1px;
  }}

  .market-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 16px;
  }}
  .market-block {{
    text-align: left;
  }}
  .market-name {{
    color: var(--text-main);
    font-size: 14px;
    font-weight: 600;
    padding-left: 10px;
    border-left: 3px solid var(--sage);
    margin-bottom: 6px;
  }}
  .market-data {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 4px;
    padding-left: 13px;
  }}
  .market-label {{
    color: var(--sentiment-main);
    font-size: 13px;
    font-weight: 500;
  }}
  .market-avg {{
    color: var(--text-muted);
    font-size: 11px;
  }}
  .market-detail {{
    color: var(--sentiment-sub);
    font-size: 11px;
    padding-left: 13px;
  }}

  .industry-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
    margin-top: 16px;
  }}
  .industry-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: rgba(183, 192, 163, 0.08);
    border-radius: 6px;
  }}
  .industry-icon {{
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: #F7F5EF;
    flex-shrink: 0;
  }}
  .industry-name {{
    color: var(--text-main);
    font-size: 12px;
    font-weight: 500;
    flex: 1;
  }}
  .industry-detail {{
    color: var(--text-muted);
    font-size: 11px;
    white-space: nowrap;
  }}

  .sentiment-events {{
    color: var(--sentiment-sub);
    font-size: 12px;
    line-height: 1.6;
    font-style: italic;
    margin-top: 20px;
    padding: 12px 16px;
    background: rgba(183, 192, 163, 0.06);
    border-radius: 6px;
    border-left: 3px solid var(--sage);
  }}

  /* 本周大事记 / 地缘时间轴 / 反向索引 共用样式 */
  .weekly-section, .geo-section, .topic-reverse-section, .search-section {{
    margin-top: 32px;
  }}
  .weekly-list {{
    list-style: none;
    padding: 0;
    margin: 12px 0 0;
  }}
  .weekly-list li {{
    padding: 8px 0;
    border-bottom: 1px dashed var(--line-soft);
    font-size: 13px;
    line-height: 1.6;
  }}
  .weekly-list li:last-child {{
    border-bottom: none;
  }}
  .weekly-list .hl-date {{
    display: inline-block;
    min-width: 50px;
    color: var(--rose);
    font-weight: 600;
    font-size: 12px;
    margin-right: 8px;
  }}
  .weekly-list a {{
    color: var(--text-main);
    text-decoration: none;
    border-bottom: 1px dotted var(--line-soft);
  }}
  .weekly-list a:hover {{
    color: var(--rose);
    border-bottom-color: var(--rose);
  }}
  .topic-reverse {{
    background: var(--card, #fff);
    border: 1px solid var(--line-soft);
    border-radius: 8px;
    margin-bottom: 8px;
    overflow: hidden;
  }}
  .topic-reverse summary {{
    padding: 10px 14px;
    cursor: pointer;
    font-size: 13px;
    list-style: none;
    user-select: none;
    transition: background 0.15s;
  }}
  .topic-reverse summary::-webkit-details-marker {{ display: none; }}
  .topic-reverse summary:hover {{
    background: rgba(213, 160, 162, 0.06);
  }}
  .topic-reverse[open] summary {{
    border-bottom: 1px solid var(--line-soft);
  }}
  .topic-reverse .weekly-list {{
    padding: 12px 16px;
  }}
  /* 顶部 Tab 栏 */
  .tab-bar {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 28px;
    padding: 0 4px;
    border-bottom: 1px solid var(--line-soft);
    flex-wrap: wrap;
  }}
  .tab-buttons {{
    display: flex;
    gap: 4px;
    flex: 1;
    min-width: 0;
  }}
  .tab-btn {{
    background: none;
    border: none;
    padding: 10px 14px;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all 0.15s;
    font-family: inherit;
    letter-spacing: 0.3px;
  }}
  .tab-btn:hover {{
    color: var(--text-main);
  }}
  .tab-btn.active {{
    color: var(--rose);
    border-bottom-color: var(--rose);
    font-weight: 600;
  }}
  .tab-search {{
    flex-shrink: 0;
    width: 220px;
  }}
  .tab-search input {{
    width: 100%;
    padding: 7px 12px;
    font-size: 13px;
    border: 1px solid var(--line-soft);
    border-radius: 16px;
    background: var(--card, #fff);
    color: var(--text-main);
    outline: none;
    transition: border-color 0.15s;
  }}
  .tab-search input:focus {{
    border-color: var(--rose);
  }}
  /* Tab 面板 */
  .tab-panel {{
    display: none;
  }}
  .tab-panel.active {{
    display: block;
  }}
  /* 全局搜索结果（跨 Tab 显示在 tab 栏下方） */
  #search-results-global {{
    margin-bottom: 16px;
  }}
  #search-results-global:not(:empty) {{
    background: var(--card, #fff);
    border: 1px solid var(--line-soft);
    border-radius: 8px;
    padding: 12px 18px;
    max-height: 400px;
    overflow-y: auto;
  }}
  /* 搜索项 */
  #search-results-global .sr-item {{
    padding: 8px 0;
    border-bottom: 1px dashed var(--line-soft);
    font-size: 13px;
    line-height: 1.6;
  }}
  #search-results-global .sr-item:last-child {{ border-bottom: none; }}
  #search-results-global .sr-date {{
    display: inline-block;
    min-width: 70px;
    color: var(--rose);
    font-weight: 600;
    font-size: 12px;
    margin-right: 8px;
  }}
  #search-results-global .sr-item a {{
    color: var(--text-main);
    text-decoration: none;
    border-bottom: 1px dotted var(--line-soft);
  }}
  #search-results-global .sr-item a:hover {{
    color: var(--rose);
    border-bottom-color: var(--rose);
  }}
  #search-results-global .sr-empty {{
    color: var(--text-muted);
    font-size: 12px;
    padding: 8px 0;
    text-align: center;
  }}
  #search-results-global .sr-highlight {{
    background: rgba(212, 166, 74, 0.25);
    padding: 0 2px;
    border-radius: 2px;
    font-weight: 600;
  }}
  /* 响应式 */
  @media (max-width: 640px) {{
    .tab-bar {{
      flex-direction: column;
      align-items: stretch;
      gap: 8px;
    }}
    .tab-search {{
      width: 100%;
    }}
  }}


  .calendar-section {{
    margin-top: 32px;
  }}
  .cal-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 32px;
    margin-top: 16px;
  }}
  .cal-month {{
    text-align: center;
  }}
  .cal-month-title {{
    color: var(--text-main);
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
  }}
  .cal-row {{
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 4px;
  }}
  .cal-header span {{
    color: var(--text-muted);
    font-size: 10px;
    padding: 4px 0;
  }}
  .cal-day {{
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    color: var(--calendar-empty);
    border-radius: 50%;
    text-decoration: none;
    transition: all 0.15s;
    margin: 0 auto;
  }}
  .cal-day.empty {{
    visibility: hidden;
  }}
  .cal-day.active {{
    background: var(--calendar-fill);
    color: #F7F5EF;
    font-weight: 500;
  }}
  .cal-day.active:hover {{
    background: var(--rose);
    transform: scale(1.1);
  }}
  .cal-day.today {{
    box-shadow: 0 0 0 2px var(--calendar-ring);
  }}
  footer {{
    text-align: center;
    margin-top: 60px;
    padding-top: 24px;
    border-top: 1px solid var(--line-soft);
    color: var(--text-muted);
    font-size: 12px;
  }}
  footer a {{
    color: var(--text-muted);
    text-decoration: none;
  }}
  footer a:hover {{
    color: var(--rose);
  }}
  @media (max-width: 600px) {{
    .today-date {{ font-size: 32px; }}
    .cal-grid {{ grid-template-columns: repeat(2, 1fr); gap: 20px; }}
    .bar-label {{ font-size: 10px; max-width: 60px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🦞 龙虾老师 · 每日不错过新闻</h1>
    <div class="subtitle">每天 08:00 · 世界新闻 / 行业宏观 / 国际局势</div>
  </header>

  <!-- 顶部 Tab 栏：左侧话题反向索引 / 地缘事件时间轴，右侧搜索框 -->
  <nav class="tab-bar">
    <div class="tab-buttons">
      <button class="tab-btn active" data-tab="main">📰 今日总览</button>
      <button class="tab-btn" data-tab="topics">🔗 话题反向索引</button>
      <button class="tab-btn" data-tab="geo">🌍 事件时间轴</button>
    </div>
    <div class="tab-search">
      <input type="text" id="search-input" placeholder="🔍 搜关键词…" />
    </div>
  </nav>
  <div id="search-results-global"></div>

  <!-- Tab 1: 今日总览（默认） -->
  <div class="tab-panel active" id="tab-main">
    <div class="today-section">
      <div class="today-label">今日早报</div>
      <div class="today-date">
        <a href="archive/{latest}.html">{format_date_big(latest) if latest else '暂无'}</a>
      </div>
      <div class="today-summary">{summary}</div>
    </div>

    {weekly_html}

    <div class="insights-section">
      <div class="section-title">近 30 天被热议的新话题 TOP 10</div>
      {bar_chart_html}
      <div class="chart-caption">从每天标题提取事件性话题（板块名/标的代码已过滤），按被提及天数排序</div>

      <div style="margin-top: 40px;">
        <div class="section-title">各市场情绪（近 30 天）</div>
        <div class="market-grid">
          {market_blocks}
        </div>
      </div>

      <div style="margin-top: 32px;">
        <div class="section-title">各行业情绪（近 30 天）</div>
        <div class="industry-grid">
          {industry_items}
        </div>
      </div>

      {events_html}
    </div>

    <div class="calendar-section">
      <div class="section-title">历史日报</div>
      {calendar_html}
    </div>
  </div>

  <!-- Tab 2: 话题反向索引 -->
  <div class="tab-panel" id="tab-topics">
    {topic_reverse_html}
  </div>

  <!-- Tab 3: 地缘事件时间轴 -->
  <div class="tab-panel" id="tab-geo">
    {geo_html}
  </div>

  <footer>
    共 {total} 期 · 更新于 {now} · <a href="https://github.com/eelaine-zhang/daily-news">GitHub</a>
  </footer>
</div>
<script>
// Tab 切换
(function() {{
  const btns = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');
  btns.forEach(btn => {{
    btn.addEventListener('click', () => {{
      const target = btn.dataset.tab;
      btns.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + target)?.classList.add('active');
      // 清空搜索结果
      const r = document.getElementById('search-results-global');
      if (r) r.innerHTML = '';
      const i = document.getElementById('search-input');
      if (i) i.value = '';
    }});
  }});
}})();

// 全站搜索
(async function() {{
  const input = document.getElementById('search-input');
  const results = document.getElementById('search-results-global');
  if (!input || !results) return;
  let index = [];
  try {{
    const r = await fetch('search_index.json');
    index = await r.json();
  }} catch (e) {{
    results.innerHTML = '<div class="sr-empty">搜索索引加载失败</div>';
    return;
  }}
  function highlight(text, kw) {{
    const re = new RegExp(kw.replace(/[.*+?^${{}}()|[\]\\]/g, '\\$&'), 'gi');
    return text.replace(re, m => `<span class="sr-highlight">${{m}}</span>`);
  }}
  let timer;
  input.addEventListener('input', () => {{
    clearTimeout(timer);
    timer = setTimeout(() => {{
      const q = input.value.trim();
      if (!q || q.length < 2) {{
        results.innerHTML = q ? '<div class="sr-empty">请输入至少 2 个字</div>' : '';
        return;
      }}
      const out = [];
      for (const day of index) {{
        for (const title of day.titles) {{
          if (title.toLowerCase().includes(q.toLowerCase())) {{
            out.push({{ date: day.date, title }});
          }}
        }}
      }}
      if (out.length === 0) {{
        results.innerHTML = `<div class="sr-empty">没有找到「${{q}}」相关的报道</div>`;
        return;
      }}
      const max = 30;
      const items = out.slice(0, max).map(r => `
        <div class="sr-item">
          <span class="sr-date">${{r.date.slice(5).replace('-', '/')}}</span>
          <a href="archive/${{r.date}}.html">${{highlight(r.title, q)}}</a>
        </div>
      `).join('');
      const more = out.length > max ? `<div class="sr-empty">共 ${{out.length}} 条结果，仅显示前 ${{max}} 条</div>` : `<div class="sr-empty">共 ${{out.length}} 条结果</div>`;
      results.innerHTML = items + more;
    }}, 200);
  }});
}})();
</script>
</body>
</html>
"""
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"✅ Generated {INDEX_HTML} with {total} entries (latest: {latest})")
    print(f"   TOP 10: {[kw for kw, _ in top10]}")
    print(f"   Sentiment: 涨{up_days} 跌{down_days} 震荡{flat_days}")

if __name__ == "__main__":
    main()
