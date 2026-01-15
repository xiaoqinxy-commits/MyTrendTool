"""
通过 Google News RSS 抓取彭博社最近 24 小时的要闻标题。
使用 requests 拉取 RSS（以便支持代理），然后用 feedparser 解析。
"""
from typing import List, Dict
import sys
import requests
import feedparser


def fetch_bloomberg_latest(proxy: str = 'http://127.0.0.1:7897', limit: int = 5) -> List[Dict[str, str]]:
    """返回列表，每项包含 title, link, summary（若有）。"""
    proxies = {'http': proxy, 'https': proxy}
    url = 'https://news.google.com/rss/search?q=when:24h+site:bloomberg.com&hl=en-US'
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        r = requests.get(url, proxies=proxies, headers=headers, timeout=20)
    except requests.RequestException as e:
        print(f'[Bloomberg RSS] 请求失败: {e}', file=sys.stderr)
        return []

    if r.status_code != 200:
        print(f'[Bloomberg RSS] HTTP {r.status_code} {r.reason}', file=sys.stderr)
        print(f'[Bloomberg RSS] 响应长度: {len(r.content)}', file=sys.stderr)
        return []

    feed = feedparser.parse(r.content)
    items: List[Dict[str, str]] = []
    for entry in feed.entries[:limit]:
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        summary = entry.get('summary', '').strip() or entry.get('description', '').strip()
        if title:
            items.append({'title': title, 'link': link, 'summary': summary})

    return items
