import streamlit as st
import feedparser
import requests
import os
import platform
from datetime import datetime
from typing import List, Dict
from googletrans import Translator

# --- 核心配置与工具函数 ---

def running_in_cloud() -> bool:
    """自动检测是否运行在云端"""
    cloud_indicators = ['STREAMLIT_RUNTIME_ENV', 'STREAMLIT_CLOUD', 'GITHUB_ACTIONS', 'HOSTNAME']
    for v in cloud_indicators:
        if os.environ.get(v):
            return True
    return platform.system() != 'Windows'

IS_CLOUD = running_in_cloud()

def safe_translate(text: str) -> str:
    """保险丝翻译：翻译失败时返回原文，绝不卡死页面"""
    if not text:
        return ""
    try:
        # 设置短超时，防止云端网络阻塞
        translator = Translator()
        return translator.translate(text, dest='zh-cn').text
    except Exception:
        return text # 失败则返回原英文

def fetch_feed(url, use_proxy: bool, proxy: str):
    """带面具的抓取函数：自动处理代理与请求头"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    actual_proxies = None
    # 仅在非云端且用户勾选时使用代理
    if use_proxy and not IS_CLOUD:
        actual_proxies = {'http': proxy, 'https': proxy}
        
    try:
        r = requests.get(url, headers=headers, proxies=actual_proxies, timeout=10)
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception:
        return feedparser.parse(url)

def parse_published(entry) -> str:
    if 'published' in entry: return entry.published
    if 'updated' in entry: return entry.updated
    return ''

# --- 界面初始化 ---

st.set_page_config(page_title='TrendTool', layout='centered')

# CSS 注入：解决手机端标题换行与卡片样式
st.markdown("""
<style>
.app-container {max-width:500px; margin:0 auto;}
/* 标题美化：强制不换行 */
.app-title {
    font-size:24px;
    font-weight:700;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
    margin:10px 0;
    text-align:center;
}
.news-card {background:#fff; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.08); padding:18px; margin-bottom:15px; border:1px solid #eee;}
.news-card a {color:#1a73e8; font-weight:700; text-decoration:none; font-size:1.1rem;}
.orig-title {color:#6b7280; font-size:0.85rem; margin-top:5px; line-height:1.2;}
.news-summary {color:#374151; font-size:0.9rem; margin-top:8px;}
.news-meta {color:#9ca3af; font-size:0.8rem; margin-top:8px;}
.section-header{border-left:4px solid #1a73e8; padding-left:10px; margin:20px 0 10px 0; font-size:1.2rem;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="app-container">', unsafe_allow_html=True)
st.markdown("<div class='app-title'>TrendTool — 要闻聚合</div>", unsafe_allow_html=True)

# 设置区域
with st.expander('⚙️ 运行设置', expanded=False):
    if IS_CLOUD:
        st.info('☁️ 已自动切换至云端直连模式')
    use_proxy = st.checkbox('使用本地代理', value=(not IS_CLOUD), disabled=IS_CLOUD)
    proxy_addr = st.text_input('代理地址', value='http://127.0.0.1:7897', disabled=IS_CLOUD)
    limit = st.slider('获取条数', 1, 10, 5)
    refresh = st.button('立即刷新数据')

# --- 数据抓取与展示逻辑 ---

if 'data' not in st.session_state or refresh:
    with st.spinner('正在同步全球资讯...'):
        # 1. 抓取路透社
        reuters = []
        feed_r = fetch_feed(f'https://news.google.com/rss/search?q=when:24h+site:reuters.com&hl=en-US', use_proxy, proxy_addr)
        for e in feed_r.entries[:limit]:
            title = e.get('title', '')
            reuters.append({
                'title': title,
                'title_zh': safe_translate(title),
                'link': e.get('link', ''),
                'summary': e.get('summary', '')[:100] + '...',
                'pub': parse_published(e)
            })

        # 2. 抓取彭博社
        bloomberg = []
        feed_b = fetch_feed(f'https://news.google.com/rss/search?q=when:24h+site:bloomberg.com&hl=en-US', use_proxy, proxy_addr)
        for e in feed_b.entries[:limit]:
            title = e.get('title', '')
            bloomberg.append({
                'title': title,
                'title_zh': safe_translate(title),
                'link': e.get('link', ''),
                'summary': e.get('summary', '')[:100] + '...',
                'pub': parse_published(e)
            })

        # 3. 抓取马斯克动态 (Google News 回退方案)
        musk = []
        feed_m = fetch_feed(f'https://news.google.com/rss/search?q=Elon+Musk+when:24h&hl=en-US', use_proxy, proxy_addr)
        for e in feed_m.entries[:limit]:
            title = e.get('title', '')
            musk.append({
                'title': title,
                'title_zh': safe_translate(title),
                'link': e.get('link', ''),
                'pub': parse_published(e)
            })

        st.session_state['data'] = {'reuters': reuters, 'bloomberg': bloomberg, 'musk': musk, 'time': datetime.now().strftime('%H:%M:%S')}

# 展示界面
data = st.session_state['data']
st.caption(f"数据更新于: {data['time']}")

# 马斯克板块
if data['musk']:
    st.markdown('<div class="section-header">马斯克动态</div>', unsafe_allow_html=True)
    for item in data['musk']:
        st.markdown(f"""
        <div class='news-card'>
            <a href='{item['link']}' target='_blank'>{item['title_zh']}</a>
            <div class='orig-title'>{item['title']}</div>
            <div class='news-meta'>{item['pub']}</div>
        </div>
        """, unsafe_allow_html=True)

# 路透社与彭博社
st.markdown('<div class="section-header">全球要闻</div>', unsafe_allow_html=True)

for source_name, items in [('路透社', data['reuters']), ('彭博社', data['bloomberg'])]:
    st.write(f"**{source_name}**")
    for item in items:
        st.markdown(f"""
        <div class='news-card'>
            <a href='{item['link']}' target='_blank'>{item['title_zh']}</a>
            <div class='orig-title'>{item['title']}</div>
            <div class='news-summary'>{item['summary']}</div>
            <div class='news-meta'>{item['pub']}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)