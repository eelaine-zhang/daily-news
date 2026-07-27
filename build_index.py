#!/usr/bin/env python3
"""Generate index.html for daily-news site (v6 Morandi minimal style)."""
import os
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict
import calendar

REPO_ROOT = Path(__file__).parent
ARCHIVE_DIR = REPO_ROOT / "archive"
INDEX_HTML = REPO_ROOT / "index.html"

DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")

# Morandi palette
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
}

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
    """Extract first meaningful line from <h4> or first <p> in the daily HTML."""
    try:
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        # Try to grab TL;DR or first h4
        m = re.search(r"<h4[^>]*>(.*?)</h4>", content, re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) > 10:
                return text[:max_len] + ("…" if len(text) > max_len else "")
        # Fallback: first <p>
        m = re.search(r"<p[^>]*>(.*?)</p>", content, re.DOTALL)
        if m:
            text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) > 10:
                return text[:max_len] + ("…" if len(text) > max_len else "")
    except Exception:
        pass
    return "今日早报已更新"

def build_calendar_html(dates_set: set, today_str: str) -> str:
    """Build monthly calendar grid with circle markers. Latest 4 months."""
    if not dates_set:
        return ""
    # Group dates by (year, month)
    by_month = defaultdict(set)
    for d in dates_set:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        by_month[(dt.year, dt.month)].add(dt.day)

    # Sort months descending, take latest 4
    sorted_months = sorted(by_month.keys(), reverse=True)[:4]
    sorted_months = sorted(sorted_months)  # ascending for display

    today = datetime.strptime(today_str, "%Y-%m-%d").date() if today_str else None

    month_blocks = []
    for (y, m) in sorted_months:
        # Build calendar for this month
        cal = calendar.monthcalendar(y, m)
        active_days = by_month[(y, m)]

        rows_html = []
        # Weekday header
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

    # Extract summary for latest
    summary = ""
    if latest:
        summary = extract_summary(ARCHIVE_DIR / f"{latest}.html")

    # Build calendar
    dates_set = set(dates)
    calendar_html = build_calendar_html(dates_set, latest)

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
  .calendar-section {{
    margin-top: 32px;
  }}
  .cal-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 24px;
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
    .cal-grid {{ grid-template-columns: repeat(2, 1fr); }}
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

if __name__ == "__main__":
    main()
