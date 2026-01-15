import streamlit as st
import feedparser
import requests
import os
import platform
from datetime import datetime
from typing import List, Dict

from googletrans import Translator

from scrapers import reuters_bot, bloomberg_bot, x_musk_bot


def fetch_feed(url: str, use_proxy: bool, proxy: str):
    headers = {'User-Agent': 'Mozilla/5.0'}
    if use_proxy and not os.environ.get('STREAMLIT_RUNTIME_ENV'):
        proxies = {'http': proxy, 'https': proxy}
        try:
            r = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            r.raise_for_status()
            return feedparser.parse(r.content)
        except Exception:
            return feedparser.parse('')
    else:
        return feedparser.parse(url)


def parse_published(entry) -> str:
    # 尝试多种字段返回 ISO 格式或人类可读时间
    if 'published' in entry:
        return entry.published
    if 'updated' in entry:
        return entry.updated
    return ''


def translate_list(texts: List[str]) -> List[str]:
    try:
        translator = Translator()
        res = []
        for t in texts:
            if not t:
                res.append('')
                continue
            try:
                tr = translator.translate(t, dest='zh-cn')
                res.append(tr.text)
            except Exception:
                res.append('')
        return res
    except Exception:
        return ['' for _ in texts]


st.set_page_config(page_title='TrendTool', layout='centered')


def running_in_cloud() -> bool:
    """尝试检测是否运行在云端（Streamlit Cloud / 常见 CI / 托管平台）。
    检测常见环境变量；如果能匹配则认为是在云端运行。
    该函数是启发式的——在需要时可以在 Streamlit Cloud 的 Settings 中设置
    环境变量 `STREAMLIT_CLOUD=1` 以确保被识别为云端。
    """
    cloud_indicators = [
        'GITHUB_ACTIONS', 'RENDER', 'VERCEL', 'HEROKU', 'STREAMLIT_CLOUD',
        'STREAMLIT_APP', 'CODESPACES', 'CI', 'DATABRICKS'
    ]
    for v in cloud_indicators:
        if os.environ.get(v):
            return True
    # 本地 Windows 系统较大概率是开发机，优先判定为本地运行
    if platform.system() == 'Windows':
        return False
    # 无明确云端信号时，默认视为本地（保守策略）
    return False

IS_CLOUD = running_in_cloud()

st.markdown("""
<style>
/* Force center and mobile-width container */
.app-container {max-width:500px; width:100%; margin:0 auto;}
html, body {overflow-x:hidden; background:#f3f4f6;}

/* Card style and spacing */
.news-card {background:#fff; border-radius:12px; box-shadow:0 6px 18px rgba(15,23,42,0.08); padding:20px; margin-bottom:15px;}
.news-card a {color:#1a73e8; font-weight:700; font-size:1.05rem; text-decoration:none;}
.orig-title {color:#6b7280; font-size:0.95rem; margin-top:8px;}
.news-meta {color:#9ca3af; font-size:0.85rem; margin-top:8px;}
.news-summary {color:#374151; font-size:0.95rem; margin-top:8px;}

/* Section headers */
.section-header{background:#f8fafc; border-left:4px solid #1a73e8; padding:8px 12px; border-radius:6px;}

/* small adjustments to Streamlit markdown containers */
.stMarkdown {padding:20px;}

/* Hide Streamlit footer and menu for cleaner mobile feel */
footer {visibility:hidden;}
#MainMenu {visibility:hidden;}

/* Responsive tweaks */
@media (max-width:480px) {
    .news-card {padding:16px;}
    .news-card a {font-size:1.05rem}
}
/* App title: smaller, single-line, no-wrap */
.app-title {
    font-size:26px; /* 24-28px 推荐值 */
    font-weight:700;
    white-space:nowrap; /* 强制一行显示，绝不换行 */
    overflow:hidden;
    text-overflow:ellipsis;
    margin:8px 0 14px 0; /* 上下间距更精致 */
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-container">', unsafe_allow_html=True)
st.markdown("<div class='app-title'>TrendTool — 要闻聚合</div>", unsafe_allow_html=True)

# Top collapsible settings
with st.expander('⚙️ 设置', expanded=False):
    if IS_CLOUD:
        st.info('检测到云端运行：已自动禁用代理（Streamlit Cloud 通常不需要本地代理）')
    # 默认在本地启用代理，云端则禁用
    use_proxy = st.checkbox('使用代理', value=(not IS_CLOUD), help='启用时将通过代理地址请求 RSS', disabled=IS_CLOUD)
    default_proxy = '' if IS_CLOUD else 'http://127.0.0.1:7897'
    proxy = st.text_input('代理地址', value=default_proxy, disabled=IS_CLOUD)
    limit = st.slider('每源最大条目数', min_value=1, max_value=10, value=5)
    refresh = st.button('抓取/刷新')

if 'last_run' not in st.session_state:
    st.session_state['last_run'] = None

if refresh or st.session_state['last_run'] is None:
    st.session_state['last_run'] = datetime.utcnow().isoformat()

    # 先使用 scrapers（当启用代理时），否则直接用 RSS
    reuters_items: List[Dict] = []
    bloom_items: List[Dict] = []
    musk_items: List[Dict] = []

    # Reuters
    if use_proxy:
        try:
            raw = reuters_bot.fetch_reuters_latest(proxy=proxy, limit=limit)
            # raw 是 (title, link)
            # 为取得发布时间，拉取 Google News feed 并匹配 title
            feed = fetch_feed('https://news.google.com/rss/search?q=when:24h+site:reuters.com&hl=en-US', use_proxy, proxy)
            feed_map = {entry.get('title',''): parse_published(entry) for entry in feed.entries}
            feed_summary = {entry.get('title',''): entry.get('summary','') or entry.get('description','') for entry in feed.entries}
            for title, link in raw:
                published = feed_map.get(title, '')
                summary = feed_summary.get(title, '')
                reuters_items.append({'source': 'reuters', 'title': title, 'link': link, 'published': published, 'summary': summary})
        except Exception:
            reuters_items = []
    else:
        feed = fetch_feed('https://news.google.com/rss/search?q=when:24h+site:reuters.com&hl=en-US', use_proxy, proxy)
        for entry in feed.entries[:limit]:
            title = entry.get('title','')
            link = entry.get('link','')
            published = parse_published(entry)
            summary = entry.get('summary','') or entry.get('description','')
            reuters_items.append({'source': 'reuters', 'title': title, 'link': link, 'published': published, 'summary': summary})

    # Bloomberg
    if use_proxy:
        try:
            raw = bloomberg_bot.fetch_bloomberg_latest(proxy=proxy, limit=limit)
            feed = fetch_feed('https://news.google.com/rss/search?q=when:24h+site:bloomberg.com&hl=en-US', use_proxy, proxy)
            feed_map = {entry.get('title',''): parse_published(entry) for entry in feed.entries}
            for it in raw:
                title = it.get('title','')
                link = it.get('link','')
                summary = it.get('summary','')
                published = feed_map.get(title, '')
                bloom_items.append({'source': 'bloomberg', 'title': title, 'link': link, 'published': published, 'summary': summary})
        except Exception:
            bloom_items = []
    else:
        feed = fetch_feed('https://news.google.com/rss/search?q=when:24h+site:bloomberg.com&hl=en-US', use_proxy, proxy)
        for entry in feed.entries[:limit]:
            title = entry.get('title','')
            link = entry.get('link','')
            published = parse_published(entry)
            summary = entry.get('summary','') or entry.get('description','')
            bloom_items.append({'source': 'bloomberg', 'title': title, 'link': link, 'published': published, 'summary': summary})

    # Musk
    try:
        raw = x_musk_bot.fetch_musk_latest(proxy=proxy if use_proxy else None, limit=limit) if use_proxy else x_musk_bot.fetch_musk_latest(proxy='', limit=limit)
    except Exception:
        raw = []
    # raw 是列表字符串，可能包含链接
    for t in raw:
        link = ''
        title = t
        if t.endswith(')') and '(' in t:
            idx = t.rfind('(')
            possible_link = t[idx+1:-1].strip()
            if possible_link.startswith('http'):
                link = possible_link
                title = t[:idx].strip()
        musk_items.append({'source': 'musk', 'title': title, 'link': link, 'published': ''})

    # 翻译所有板块标题（马斯克/路透社/彭博社）为中文
    reuters_titles = [i['title'] for i in reuters_items]
    bloom_titles = [i['title'] for i in bloom_items]
    musk_titles = [i['title'] for i in musk_items]
    trans_reuters = translate_list(reuters_titles)
    trans_bloom = translate_list(bloom_titles)
    trans_musk = translate_list(musk_titles)
    for i, it in enumerate(reuters_items):
        it['title_zh'] = trans_reuters[i] if i < len(trans_reuters) else ''
    for i, it in enumerate(bloom_items):
        it['title_zh'] = trans_bloom[i] if i < len(trans_bloom) else ''
    for i, it in enumerate(musk_items):
        it['title_zh'] = trans_musk[i] if i < len(trans_musk) else ''

    # 保存到 session
    st.session_state['reuters'] = reuters_items
    st.session_state['bloomberg'] = bloom_items
    st.session_state['musk'] = musk_items

else:
    reuters_items = st.session_state.get('reuters', [])
    bloom_items = st.session_state.get('bloomberg', [])
    musk_items = st.session_state.get('musk', [])

st.markdown(f"**上次抓取时间:** {st.session_state.get('last_run','-')}")

# 马斯克卡片（若有），显示中文大标题及原文小字
if musk_items:
        st.subheader('马斯克最新动态')
        for item in musk_items:
                title = item.get('title','')
                title_zh = item.get('title_zh','')
                link = item.get('link','')
                pub = item.get('published','')
                card = f"""
                <div class='news-card'>
                    <a href='{link or '#'}' target='_blank'>{title_zh or title}</a>
                    <div class='orig-title'>{title if title_zh else ''}</div>
                    <div class='news-meta'>{'· ' + pub if pub else ''}</div>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

# 分区：路透社 与 彭博社（卡片式）
st.header('要闻')

st.markdown('<div style="display:flex; flex-direction:column; gap:8px;">', unsafe_allow_html=True)

# Reuters 列表
if reuters_items:
    st.markdown('<h3 class="section-header">路透社</h3>', unsafe_allow_html=True)
    for item in reuters_items:
        title = item.get('title','')
        title_zh = item.get('title_zh','')
        link = item.get('link','')
        pub = item.get('published','')
        display_title = title_zh or title
        card = f"""
        <div class='news-card'>
            <a href='{link}' target='_blank'>{display_title}</a>
            <div class='orig-title'>{title if title_zh else ''}</div>
            <div class='news-summary'>{item.get('summary','')}</div>
            <div class='news-meta'>{pub}</div>
        </div>
        """
        st.markdown(card, unsafe_allow_html=True)

# Bloomberg 列表
if bloom_items:
        st.markdown('<h3 class="section-header" style="margin-top:12px">彭博社</h3>', unsafe_allow_html=True)
        for item in bloom_items:
                title = item.get('title','')
                title_zh = item.get('title_zh','')
                link = item.get('link','')
                pub = item.get('published','')
                summary = item.get('summary','')
                display_title = title_zh or title
                card = f"""
                <div class='news-card'>
                    <a href='{link or '#'}' target='_blank'>{display_title}</a>
                    <div class='orig-title'>{title if title_zh else ''}</div>
                    <div class='news-summary'>{summary}</div>
                    <div class='news-meta'>{pub}</div>
                </div>
                """
                st.markdown(card, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('\n---\n')
st.write('数据来自 Google News RSS 与 Nitter / scrapers（如启用代理）')
st.markdown('</div>', unsafe_allow_html=True)
