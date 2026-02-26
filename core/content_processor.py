"""内容处理器 - 统一处理各种类型的输入内容"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import json


@dataclass
class ContentItem:
    """内容项数据结构"""
    id: str
    source_type: str  # url, pdf, markdown, image
    source_path: str
    title: Optional[str] = None
    content: Optional[str] = None
    raw_content: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
        if self.tags is None:
            self.tags = []
    
    def generate_id(self) -> str:
        """基于内容生成唯一ID"""
        content_hash = hashlib.sha256(
            f"{self.source_type}:{self.source_path}".encode()
        ).hexdigest()[:16]
        return f"note_{content_hash}"


class ContentProcessor(ABC):
    """内容处理器抽象基类"""
    
    @abstractmethod
    def can_process(self, source: str) -> bool:
        """检查是否能处理该来源"""
        pass
    
    @abstractmethod
    def process(self, source: str) -> ContentItem:
        """处理内容并返回 ContentItem"""
        pass
    
    @abstractmethod
    def extract_text(self, content_item: ContentItem) -> str:
        """提取纯文本内容用于向量化"""
        pass


class NoteSystem:
    """笔记系统主类"""
    
    def __init__(self):
        self.processors: List[ContentProcessor] = []
        self.content_items: Dict[str, ContentItem] = {}
    
    def register_processor(self, processor: ContentProcessor):
        """注册内容处理器"""
        self.processors.append(processor)
    
    def add_content(self, source: str, source_type: str = None) -> ContentItem:
        """
        添加内容到系统
        
        Args:
            source: 内容来源（URL、文件路径等）
            source_type: 指定内容类型（可选）
        
        Returns:
            ContentItem: 处理后的内容项
        """
        # 找到合适的处理器
        for processor in self.processors:
            if processor.can_process(source):
                item = processor.process(source)
                self.content_items[item.id] = item
                return item
        
        raise ValueError(f"No processor found for source: {source}")
    
    def add_url(self, url: str) -> ContentItem:
        """添加网页链接"""
        return self.add_content(url, "url")
    
    def add_pdf(self, file_path: str) -> ContentItem:
        """添加 PDF 文件"""
        return self.add_content(file_path, "pdf")
    
    def add_markdown(self, file_path: str) -> ContentItem:
        """添加 Markdown 文件"""
        return self.add_content(file_path, "markdown")
    
    def add_image(self, file_path: str) -> ContentItem:
        """添加图片文件"""
        return self.add_content(file_path, "image")
    
    def get_note(self, note_id: str) -> Optional[ContentItem]:
        """获取指定笔记"""
        return self.content_items.get(note_id)
    
    def list_notes(self) -> List[ContentItem]:
        """列出所有笔记"""
        return list(self.content_items.values())
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        基于知识库回答问题
        
        核心原则：无来源不回答
        
        Args:
            question: 用户问题
        
        Returns:
            {
                "answer": str,           # 回答内容
                "sources": List[str],    # 来源笔记ID列表
                "confidence": float,     # 置信度
                "related_notes": List[str]  # 相关笔记
            }
        """
        # TODO: 实现基于向量检索和知识图谱的问答
        # 这是核心功能，需要结合 vector_store 和 knowledge_graph
        
        return {
            "answer": "问答功能尚未实现，请先配置向量数据库和LLM",
            "sources": [],
            "confidence": 0,
            "related_notes": []
        }
