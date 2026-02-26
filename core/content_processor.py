"""内容处理器 - 统一处理各种类型的输入内容"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib


@dataclass
class ContentItem:
    """内容项数据结构"""
    id: str
    source_type: str  # url, pdf, markdown, image
    source_path: str
    title: Optional[str] = None
    content: Optional[str] = None
    raw_content: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    vector_ids: List[str] = field(default_factory=list)
    entities: List[Dict] = field(default_factory=list)  # 提取的实体
    relations: List[Dict] = field(default_factory=list)  # 提取的关系
    
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
    
    def __init__(self, vector_store=None, knowledge_graph=None):
        self.processors: List[ContentProcessor] = []
        self.content_items: Dict[str, ContentItem] = {}
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
    
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
        processor = None
        for p in self.processors:
            if p.can_process(source):
                processor = p
                break
        
        if not processor:
            raise ValueError(f"No processor found for source: {source}")
        
        # 处理内容
        item = processor.process(source)
        
        # 保存到内存
        self.content_items[item.id] = item
        
        # 向量存储
        if self.vector_store and item.content:
            try:
                vector_ids = self.vector_store.add_note(
                    note_id=item.id,
                    title=item.title or "Untitled",
                    content=item.content,
                    metadata={
                        "source_type": item.source_type,
                        "source_path": item.source_path,
                        "tags": item.tags
                    }
                )
                item.vector_ids = vector_ids
                print(f"✓ Vectorized: {len(vector_ids)} chunks")
            except Exception as e:
                print(f"⚠ Vectorization failed: {e}")
        
        # 知识图谱（提取实体和关系）
        if self.knowledge_graph and self.knowledge_graph.is_connected() and item.content:
            try:
                from core.entity_extraction import extract_from_note
                from core.llm import get_llm_service
                
                llm = get_llm_service()
                result = extract_from_note(item, llm)
                
                entities = result.get("entities", [])
                relations = result.get("relations", [])
                
                # 保存到笔记
                item.entities = [
                    {"id": e.id, "name": e.name, "type": e.entity_type}
                    for e in entities
                ]
                item.relations = [
                    {"source": r.source, "target": r.target, "type": r.relation_type}
                    for r in relations
                ]
                
                # 添加到知识图谱
                self.knowledge_graph.add_note_with_entities(
                    note_id=item.id,
                    note_title=item.title or "Untitled",
                    entities=entities,
                    relations=relations
                )
                print(f"✓ Knowledge graph: {len(entities)} entities, {len(relations)} relations")
                
            except Exception as e:
                print(f"⚠ Knowledge graph extraction failed: {e}")
        
        return item
    
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
    
    def delete_note(self, note_id: str) -> bool:
        """删除笔记"""
        if note_id not in self.content_items:
            return False
        
        # 删除向量
        if self.vector_store:
            try:
                self.vector_store.delete(note_id)
            except Exception as e:
                print(f"⚠ Failed to delete vectors: {e}")
        
        # 删除知识图谱
        if self.knowledge_graph:
            try:
                self.knowledge_graph.delete_note(note_id)
            except Exception as e:
                print(f"⚠ Failed to delete from graph: {e}")
        
        # 删除内存中的记录
        del self.content_items[note_id]
        return True
    
    def ask(self, question: str) -> Dict[str, Any]:
        """
        基于知识库回答问题
        
        核心原则：无来源不回答
        """
        if not self.vector_store:
            return {
                "answer": "向量数据库未配置",
                "sources": [],
                "confidence": 0,
                "has_sufficient_sources": False,
                "source_chunks": []
            }
        
        from core.query_engine import QueryEngine
        from core.llm import get_llm_service
        
        engine = QueryEngine(
            vector_store=self.vector_store,
            knowledge_graph=self.knowledge_graph,
            llm_service=get_llm_service()
        )
        answer = engine.query(question)
        
        return {
            "answer": answer.content,
            "sources": answer.sources,
            "confidence": answer.confidence,
            "has_sufficient_sources": answer.has_sufficient_sources,
            "source_chunks": [
                {
                    "note_id": c["note_id"],
                    "title": c.get("title"),
                    "content": c["content"][:200] + "...",
                    "similarity": c["similarity"]
                }
                for c in answer.source_chunks
            ]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        stats = {
            "total_notes": len(self.content_items),
            "notes_by_type": {},
            "vector_count": 0,
            "graph_stats": {"notes": 0, "entities": 0, "relations": 0}
        }
        
        # 按类型统计
        for note in self.content_items.values():
            t = note.source_type
            stats["notes_by_type"][t] = stats["notes_by_type"].get(t, 0) + 1
        
        # 向量统计
        if self.vector_store:
            try:
                stats["vector_count"] = self.vector_store.count()
            except:
                pass
        
        # 图谱统计
        if self.knowledge_graph:
            try:
                stats["graph_stats"] = self.knowledge_graph.get_stats()
            except:
                pass
        
        return stats
