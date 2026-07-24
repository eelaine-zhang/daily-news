#!/usr/bin/env python3
"""Generate index.html for daily-news site.

Scans archive/*.html, builds a reverse-chronological index.
"""
import os
import re
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent
ARCHIVE_DIR = REPO_ROOT / "archive"
INDEX_HTML = REPO_ROOT / "index.html"

# Match YYYY-MM-DD.html (skip -view, .old, etc.)
DATE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.html$")

def format_date_cn(date_str: str) -> str:
    """2026-07-24 -> 2026年7月24日 周四"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    wd = weekdays[dt.weekday()]
    return f"{dt.year}年{dt.month}月{dt.day}日 {wd}"

def main():
    dates = []
    for f in ARCHIVE_DIR.iterdir():
        m = DATE_PATTERN.match(f.name)
        if m:
            dates.append(m.group(1))
    dates.sort(reverse=True)

    if not dates:
        latest = None
    else:
        latest = dates[0]

    items_html = []
    for d in dates:
        cn = format_date_cn(d)
        is_latest = (d == latest)
        badge = '<span class="badge-latest">最新</span>' if is_latest else ''
        items_html.append(
            f'<li class="news-item{" latest" if is_latest else ""}">'
            f'<a href="archive/{d}.html">'
            f'<span class="date">{cn}</span>'
            f'<span class="date-iso">{d}</span>'
            f'{badge}'
            f'</a>'
            f'</li>'
        )

    items_str = "\n      ".join(items_html)
    total = len(dates)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦞 龙虾老师 · 每日不错过新闻</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: #0f1419;
    color: #e8e8e8;
    min-height: 100vh;
    padding: 20px;
  }}
  .container {{
    max-width: 720px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    padding: 40px 20px 30px;
    border-bottom: 2px solid #ff6b6b;
    margin-bottom: 30px;
  }}
  h1 {{
    font-size: 28px;
    color: #ff6b6b;
    margin-bottom: 8px;
  }}
  .subtitle {{
    color: #999;
    font-size: 14px;
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 16px;
    font-size: 13px;
    color: #888;
  }}
  .stats strong {{ color: #ff6b6b; }}
  .latest-card {{
    background: linear-gradient(135deg, #1a1f2e 0%, #2a1f2e 100%);
    border: 1px solid #ff6b6b;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 30px;
    text-align: center;
  }}
  .latest-card .label {{
    color: #ff6b6b;
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .latest-card a {{
    color: #fff;
    font-size: 22px;
    text-decoration: none;
    font-weight: 600;
    display: block;
    margin-top: 8px;
  }}
  .latest-card a:hover {{ color: #ff6b6b; }}
  h2 {{
    font-size: 18px;
    color: #ccc;
    margin-bottom: 16px;
    padding-left: 4px;
  }}
  ul.news-list {{
    list-style: none;
  }}
  li.news-item a {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 18px;
    background: #1a1f2e;
    border: 1px solid #2a2f3e;
    border-radius: 8px;
    margin-bottom: 8px;
    text-decoration: none;
    color: #e8e8e8;
    transition: all 0.15s;
  }}
  li.news-item a:hover {{
    border-color: #ff6b6b;
    background: #1f2536;
    transform: translateX(4px);
  }}
  li.news-item.latest a {{
    border-color: #ff6b6b;
    background: linear-gradient(90deg, #1f1a2e 0%, #1a1f2e 100%);
  }}
  .date {{
    font-weight: 600;
    font-size: 15px;
    flex: 1;
  }}
  .date-iso {{
    color: #888;
    font-size: 13px;
    font-family: "SF Mono", Monaco, monospace;
  }}
  .badge-latest {{
    background: #ff6b6b;
    color: #0f1419;
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 700;
  }}
  footer {{
    text-align: center;
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid #2a2f3e;
    color: #666;
    font-size: 12px;
  }}
  @media (max-width: 600px) {{
    h1 {{ font-size: 22px; }}
    .latest-card a {{ font-size: 18px; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🦞 龙虾老师 · 每日不错过新闻</h1>
    <div class="subtitle">每天 08:00 自动更新 · 世界新闻 / 行业宏观 / 国际局势 / 重要资讯</div>
    <div class="stats">
      <span>共 <strong>{total}</strong> 期</span>
      <span>·</span>
      <span>更新于 {now}</span>
    </div>
  </header>

  <div class="latest-card">
    <div class="label">📌 今日早报</div>
    <a href="archive/{latest}.html">{format_date_cn(latest) if latest else '暂无'}</a>
  </div>

  <h2>📚 历史日报</h2>
  <ul class="news-list">
      {items_str}
  </ul>

  <footer>
    Powered by 龙虾老师 🦞 · <a href="https://github.com/eelaine-zhang/daily-news" style="color:#888;">GitHub</a>
  </footer>
</div>
</body>
</html>
"""
    INDEX_HTML.write_text(html, encoding="utf-8")
    print(f"✅ Generated {INDEX_HTML} with {total} entries (latest: {latest})")

if __name__ == "__main__":
    main()
