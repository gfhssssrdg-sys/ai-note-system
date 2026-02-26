"""Web 抓取器 - 获取和处理网页内容"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
import re

from core.content_processor import ContentProcessor, ContentItem


class WebFetcher(ContentProcessor):
    """网页内容抓取处理器"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AINoteBot/1.0)'
        })
    
    def can_process(self, source: str) -> bool:
        """检查是否为 URL"""
        return source.startswith(('http://', 'https://'))
    
    def process(self, source: str) -> ContentItem:
        """抓取并处理网页"""
        # 获取页面内容
        response = self.session.get(source, timeout=self.timeout)
        response.raise_for_status()
        
        # 解析 HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取标题
        title = self._extract_title(soup)
        
        # 提取正文
        content = self._extract_content(soup)
        
        # 提取元数据
        metadata = self._extract_metadata(soup, source)
        
        # 创建 ContentItem
        item = ContentItem(
            id="",
            source_type="url",
            source_path=source,
            title=title,
            content=content,
            raw_content=response.content,
            metadata=metadata
        )
        item.id = item.generate_id()
        
        return item
    
    def extract_text(self, content_item: ContentItem) -> str:
        """提取纯文本"""
        if content_item.content:
            return content_item.content
        
        soup = BeautifulSoup(content_item.raw_content, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """提取页面标题"""
        # 尝试各种标题标签
        for tag in ['h1', 'h2', 'title']:
            elem = soup.find(tag)
            if elem:
                return elem.get_text(strip=True)
        return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取页面正文内容"""
        # 移除脚本和样式
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
        
        # 尝试找到主要内容区域
        main_content = None
        
        # 常见的文章容器
        for selector in ['article', 'main', '.post-content', '.article-content', 
                         '.entry-content', '#content', '[role="main"]']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body or soup
        
        # 提取文本
        text = main_content.get_text(separator='\n', strip=True)
        
        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """提取元数据"""
        metadata = {
            'url': url,
            'domain': urlparse(url).netloc,
        }
        
        # Open Graph 标签
        for prop in ['og:title', 'og:description', 'og:author', 'og:published_time']:
            tag = soup.find('meta', property=prop)
            if tag:
                key = prop.replace('og:', '')
                metadata[key] = tag.get('content')
        
        # 普通 meta 标签
        for name in ['description', 'keywords', 'author']:
            tag = soup.find('meta', attrs={'name': name})
            if tag:
                metadata[name] = tag.get('content')
        
        # 提取所有链接
        links = []
        for a in soup.find_all('a', href=True):
            href = urljoin(url, a['href'])
            if href.startswith('http'):
                links.append({
                    'url': href,
                    'text': a.get_text(strip=True)[:100]
                })
        metadata['links'] = links[:50]  # 最多保存50个链接
        
        return metadata
