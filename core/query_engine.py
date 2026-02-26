"""查询引擎 - 处理用户问题并基于知识库回答"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from core.vector_store import VectorStore, ChromaVectorStore
from core.embedding import get_embedding_service
from core.llm import LLMService, get_llm_service


@dataclass
class Answer:
    """回答数据结构"""
    content: str
    sources: List[str]  # 来源笔记ID
    confidence: float  # 0-1
    related_notes: List[str]
    has_sufficient_sources: bool  # 是否有足够来源支持回答
    source_chunks: List[Dict]  # 来源片段详情


class QueryEngine:
    """
    查询引擎
    
    核心原则：无证据不回答
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        knowledge_graph=None,
        llm_service: Optional[LLMService] = None
    ):
        self.vector_store = vector_store or ChromaVectorStore()
        self.knowledge_graph = knowledge_graph
        self.llm = llm_service or get_llm_service()
        self.embedding_service = get_embedding_service()
        
        # 配置
        self.min_similarity_threshold = 0.6  # 最低相似度阈值
        self.max_context_chunks = 5  # 最大上下文块数
    
    def query(self, question: str, top_k: int = 5) -> Answer:
        """
        处理用户查询
        
        流程：
        1. 向量检索相关文档
        2. 检查置信度
        3. 使用 LLM 生成回答（仅在有足够来源时）
        """
        # 1. 向量检索
        retrieval_results = self.vector_store.search(
            query=question,
            top_k=top_k
        )
        
        # 2. 检查是否有足够相关的来源
        if not retrieval_results:
            return self._empty_answer("抱歉，我的知识库中没有相关信息。请自行搜集资料。")
        
        # 过滤低相似度结果
        relevant_sources = [
            r for r in retrieval_results 
            if r['similarity'] >= self.min_similarity_threshold
        ]
        
        if not relevant_sources:
            best_match = retrieval_results[0]
            return self._empty_answer(
                f"抱歉，我的知识库中没有找到足够相关的信息（最相关度仅 {best_match['similarity']:.1%}）。请自行搜集资料。"
            )
        
        # 3. 按 note_id 去重并限制数量
        seen_notes = set()
        unique_sources = []
        for r in relevant_sources:
            if r['note_id'] not in seen_notes and len(unique_sources) < self.max_context_chunks:
                seen_notes.add(r['note_id'])
                unique_sources.append(r)
        
        # 4. 构造上下文
        source_note_ids = list(seen_notes)
        context = self._build_context(unique_sources)
        
        # 5. 通过知识图谱扩展相关笔记
        related_notes = self._expand_via_graph(source_note_ids)
        
        # 6. 使用 LLM 生成回答
        answer_content = self.llm.answer_question(
            question=question,
            context=context,
            sources=unique_sources
        )
        
        # 7. 计算整体置信度
        avg_similarity = sum(r['similarity'] for r in unique_sources) / len(unique_sources)
        
        return Answer(
            content=answer_content,
            sources=source_note_ids,
            confidence=avg_similarity,
            related_notes=related_notes,
            has_sufficient_sources=True,
            source_chunks=unique_sources
        )
    
    def _empty_answer(self, message: str) -> Answer:
        """返回空回答"""
        return Answer(
            content=message,
            sources=[],
            confidence=0.0,
            related_notes=[],
            has_sufficient_sources=False,
            source_chunks=[]
        )
    
    def _expand_via_graph(self, source_ids: List[str]) -> List[str]:
        """通过知识图谱扩展相关笔记"""
        if not self.knowledge_graph:
            return []
        
        related = set()
        # TODO: 实现图谱查询获取相关笔记
        return list(related)
    
    def _build_context(self, sources: List[Dict]) -> str:
        """构造上下文"""
        context_parts = []
        for i, source in enumerate(sources, 1):
            title = source.get('title', 'Untitled')
            content = source.get('content', '')
            context_parts.append(f"[{i}] 来源: {title}\n{content}\n")
        return "\n".join(context_parts)
