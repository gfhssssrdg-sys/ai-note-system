"""Markdown 解析器"""

import re
from pathlib import Path
from typing import Dict, Any, List
import markdown
from bs4 import BeautifulSoup

from core.content_processor import ContentProcessor, ContentItem


class MarkdownParser(ContentProcessor):
    """Markdown 文件处理器"""
    
    def __init__(self):
        self.md = markdown.Markdown(extensions=['meta', 'toc', 'fenced_code'])
    
    def can_process(self, source: str) -> bool:
        """检查是否为 Markdown 文件"""
        return source.lower().endswith(('.md', '.markdown', '.mdown'))
    
    def process(self, source: str) -> ContentItem:
        """解析 Markdown 文件"""
        file_path = Path(source)
        
        # 读取文件
        content = file_path.read_text(encoding='utf-8')
        
        # 解析元数据
        metadata = self._parse_metadata(content)
        metadata['filename'] = file_path.name
        metadata['file_path'] = str(file_path.absolute())
        
        # 提取标题
        title = metadata.get('title') or self._extract_title(content) or file_path.stem
        
        # 转换为 HTML（用于进一步处理）
        html_content = self.md.convert(content)
        
        # 提取纯文本
        plain_text = self._html_to_text(html_content)
        
        # 提取链接
        links = self._extract_links(content)
        metadata['links'] = links
        
        # 提取标签
        tags = self._extract_tags(content)
        
        # 创建 ContentItem
        item = ContentItem(
            id="",
            source_type="markdown",
            source_path=str(file_path.absolute()),
            title=title,
            content=plain_text,
            raw_content=content.encode('utf-8'),
            metadata=metadata,
            tags=tags
        )
        item.id = item.generate_id()
        
        # 重置 markdown 解析器
        self.md.reset()
        
        return item
    
    def extract_text(self, content_item: ContentItem) -> str:
        """提取纯文本"""
        return content_item.content or ""
    
    def _parse_metadata(self, content: str) -> Dict[str, Any]:
        """解析 YAML frontmatter"""
        metadata = {}
        
        # 匹配 YAML frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            yaml_content = match.group(1)
            # 简单的 YAML 解析
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    metadata[key] = value
        
        return metadata
    
    def _extract_title(self, content: str) -> str:
        """从 Markdown 提取一级标题"""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else None
    
    def _html_to_text(self, html: str) -> str:
        """HTML 转纯文本"""
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    
    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """提取 Markdown 中的链接"""
        links = []
        # 匹配 [text](url) 格式
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(pattern, content):
            links.append({
                'text': match.group(1),
                'url': match.group(2)
            })
        return links
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取标签（#tag 格式）"""
        # 匹配 #tag 但不匹配代码块中的内容
        tags = set()
        for match in re.finditer(r'#(\w+)', content):
            tag = match.group(1)
            if not tag.isdigit():  # 排除纯数字
                tags.add(tag)
        return list(tags)
