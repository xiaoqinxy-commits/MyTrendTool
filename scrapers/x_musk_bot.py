"""
通过 nitter 镜像抓取 Elon Musk 的最新推文（免登录）。
目标：https://nitter.net/elonmusk
返回推文文本列表（最新在前）。
"""
from typing import List, Optional
import sys
import requests
import feedparser


def fetch_musk_latest(proxy: Optional[str] = None, limit: int = 5) -> List[str]:
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    headers = {'User-Agent': 'Mozilla/5.0'}

    nitter_rss_instances = [
        'https://nitter.privacydev.net/elonmusk/rss',
        'https://nitter.poast.org/elonmusk/rss',
        'https://nitter.42l.fr/elonmusk/rss',
    ]

    feed = None
    used = None
    for rss in nitter_rss_instances:
        try:
            if proxies:
                r = requests.get(rss, headers=headers, proxies=proxies, timeout=15)
            else:
                r = requests.get(rss, headers=headers, timeout=15)
        except requests.RequestException as e:
            print(f'[Nitter RSS] 请求 {rss} 失败: {e}', file=sys.stderr)
            continue
        if r.status_code != 200:
            print(f'[Nitter RSS] {rss} 返回 HTTP {r.status_code} {r.reason}', file=sys.stderr)
            print(f'[Nitter RSS] 响应长度: {len(r.content)}', file=sys.stderr)
            continue
        feed = feedparser.parse(r.content)
        used = rss
        break

    if not feed or not feed.entries:
        # 回退方案：使用 Google News RSS 搜索 Elon Musk 相关新闻
        print('[Nitter RSS] 所有实例均无法获取或没有条目，尝试使用 Google News RSS 作为回退。', file=sys.stderr)
        try:
            g_url = 'https://news.google.com/rss/search?q=Elon+Musk&hl=en-US'
            if proxies:
                r = requests.get(g_url, headers=headers, proxies=proxies, timeout=15)
            else:
                r = requests.get(g_url, headers=headers, timeout=15)
            if r.status_code == 200:
                gfeed = feedparser.parse(r.content)
                tweets = []
                for entry in gfeed.entries[:limit]:
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '').strip()
                    if title:
                        tweets.append(f"{title}  ({link})" if link else title)
                if tweets:
                    return tweets[:limit]
            else:
                print(f'[Google News RSS] HTTP {r.status_code} {r.reason}', file=sys.stderr)
        except Exception as e:
            print(f'[Google News RSS] 请求失败: {e}', file=sys.stderr)

        print('[Musk] 未能获取到任何推文或相关新闻。', file=sys.stderr)
        return []

    tweets: List[str] = []
    for entry in feed.entries[:limit]:
        text = entry.get('title') or entry.get('summary') or ''
        text = (text or '').strip()
        link = entry.get('link', '').strip()
        if text:
            if link:
                tweets.append(f"{text}  ({link})")
            else:
                tweets.append(text)

    return tweets[:limit]
