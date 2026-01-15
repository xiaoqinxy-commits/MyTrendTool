"""
通过 Google News RSS 抓取路透社最近 24 小时内的新闻标题与链接。
使用 requests 拉取 RSS（以便支持代理），然后用 feedparser 解析。
"""
from typing import List, Tuple, Optional
import sys
import requests
import feedparser


def fetch_reuters_latest(proxy: Optional[str] = None, limit: int = 5) -> List[Tuple[str, str]]:
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    url = 'https://news.google.com/rss/search?q=when:24h+site:reuters.com&hl=en-US'
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        if proxies:
            r = requests.get(url, proxies=proxies, headers=headers, timeout=20)
        else:
            r = requests.get(url, headers=headers, timeout=20)
    except requests.RequestException as e:
        print(f'[Reuters RSS] 请求失败: {e}', file=sys.stderr)
        return []

    if r.status_code != 200:
        print(f'[Reuters RSS] HTTP {r.status_code} {r.reason}', file=sys.stderr)
        print(f'[Reuters RSS] 响应长度: {len(r.content)}', file=sys.stderr)
        return []

    feed = feedparser.parse(r.content)
    results: List[Tuple[str, str]] = []
    for entry in feed.entries[:limit]:
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        if title and link:
            results.append((title, link))

    return results
