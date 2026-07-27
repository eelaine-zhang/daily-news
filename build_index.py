#!/usr/bin/env python3
"""Generate index.html for daily-news site (v6 Morandi minimal style)."""
import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter
import calendar

REPO_ROOT = Path(__file__).parent
ARCHIVE_DIR = REPO_ROOT / "archive"
INDEX_HTML = REPO_ROOT / "index.html"

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


def analyze_keywords(dates: list, days: int = 30) -> list:
    """Count keyword frequency over the last N days. Returns top 10."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [d for d in dates if d >= cutoff]
    counter = Counter()
    for d in recent:
        html_path = ARCHIVE_DIR / f"{d}.html"
        try:
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", content)
            counted_in_doc = set()
            for kw in KEYWORD_LIST:
                if kw in text and kw not in counted_in_doc:
                    # Count each doc once per keyword (avoid one article dominating)
                    counter[kw] += 1
                    counted_in_doc.add(kw)
        except Exception:
            continue
    return counter.most_common(10)


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


def render_bar_chart(top10: list) -> str:
    """Render vertical bar chart with 10 morandi colors."""
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
    return f'<div class="bar-chart">{"".join(bars_html)}</div>'


def build_calendar_html(dates_set: set, today_str: str) -> str:
    if not dates_set:
        return ""
    by_month = defaultdict(set)
    for d in dates_set:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        by_month[(dt.year, dt.month)].add(dt.day)

    sorted_months = sorted(by_month.keys(), reverse=True)[:4]
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
    top10 = analyze_keywords(dates, days=30)
    bar_chart_html = render_bar_chart(top10)
    up_days, down_days, flat_days, sentiment_total, major_events = analyze_sentiment(dates, days=30)
    market_sent = analyze_market_sentiment(dates, days=30)
    industry_sent = analyze_industry_sentiment(dates, days=30)

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

  <div class="today-section">
    <div class="today-label">今日早报</div>
    <div class="today-date">
      <a href="archive/{latest}.html">{format_date_big(latest) if latest else '暂无'}</a>
    </div>
    <div class="today-summary">{summary}</div>
  </div>

  <div class="insights-section">
    <div class="section-title">近 30 天 TOP 10 高频关键词</div>
    {bar_chart_html}
    <div class="chart-caption">统计每个关键词在近 30 天日报中出现的期数</div>

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

  <footer>
    共 {total} 期 · 更新于 {now} · <a href="https://github.com/eelaine-zhang/daily-news">GitHub</a>
  </footer>
</div>
</body>
</html>
"""
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"✅ Generated {INDEX_HTML} with {total} entries (latest: {latest})")
    print(f"   TOP 10: {[kw for kw, _ in top10]}")
    print(f"   Sentiment: 涨{up_days} 跌{down_days} 震荡{flat_days}")

if __name__ == "__main__":
    main()
