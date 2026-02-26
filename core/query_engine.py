"""查询引擎 - 处理用户问题并基于知识库回答"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class Answer:
    """回答数据结构"""
    content: str
    sources: List[str]  # 来源笔记ID
    confidence: float  # 0-1
    related_notes: List[str]
    has_sufficient_sources: bool  # 是否有足够来源支持回答


class QueryEngine:
    """
    查询引擎
    
    核心原则：无证据不回答
    """
    
    def __init__(self, vector_store, knowledge_graph, llm_client=None):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.llm = llm_client
        self.min_confidence_threshold = 0.6  # 最低置信度阈值
        self.max_answer_without_source = 0  # 不允许无来源回答
    
    def query(self, question: str, top_k: int = 5) -> Answer:
        """
        处理用户查询
        
        流程：
        1. 向量化问题
        2. 检索相关文档
        3. 检查置信度
        4. 生成回答（仅在有足够来源时）
        """
        # 1. 获取问题的向量表示
        query_embedding = self._embed(question)
        
        # 2. 向量检索
        retrieval_results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k
        )
        
        # 3. 检查是否有足够相关的来源
        if not retrieval_results or retrieval_results[0]['distance'] > 0.8:
            # 没有足够相关的来源
            return Answer(
                content="抱歉，我的知识库中没有相关信息。请自行搜集资料。",
                sources=[],
                confidence=0.0,
                related_notes=[],
                has_sufficient_sources=False
            )
        
        # 4. 过滤低置信度结果
        relevant_sources = [
            r for r in retrieval_results 
            if r['distance'] <= 0.8
        ]
        
        if not relevant_sources:
            return Answer(
                content="抱歉，我的知识库中没有相关信息。请自行搜集资料。",
                sources=[],
                confidence=0.0,
                related_notes=[],
                has_sufficient_sources=False
            )
        
        # 5. 基于知识图谱扩展相关笔记
        source_note_ids = list(set(r['note_id'] for r in relevant_sources))
        related_notes = self._expand_via_graph(source_note_ids)
        
        # 6. 构造上下文
        context = self._build_context(relevant_sources)
        
        # 7. 生成回答
        if self.llm:
            answer_content = self._generate_answer_with_llm(question, context)
        else:
            answer_content = self._generate_answer_simple(question, relevant_sources)
        
        # 8. 计算整体置信度
        avg_distance = sum(r['distance'] for r in relevant_sources) / len(relevant_sources)
        confidence = 1 - avg_distance  # 距离越小置信度越高
        
        return Answer(
            content=answer_content,
            sources=source_note_ids,
            confidence=confidence,
            related_notes=related_notes,
            has_sufficient_sources=True
        )
    
    def _embed(self, text: str) -> List[float]:
        """文本向量化"""
        # TODO: 调用嵌入模型
        # 临时返回空向量，实际应调用 OpenAI 或其他嵌入服务
        return [0.0] * 1536
    
    def _expand_via_graph(self, source_ids: List[str]) -> List[str]:
        """通过知识图谱扩展相关笔记"""
        related = set()
        for note_id in source_ids:
            # 获取同一实体的其他笔记
            # TODO: 实现图谱查询
            pass
        return list(related)
    
    def _build_context(self, sources: List[Dict]) -> str:
        """构建LLM上下文"""
        context_parts = []
        for i, source in enumerate(sources, 1):
            context_parts.append(f"[来源 {i}]\n{source['content']}\n")
        return "\n".join(context_parts)
    
    def _generate_answer_with_llm(self, question: str, context: str) -> str:
        """使用LLM生成回答"""
        if not self.llm:
            return self._generate_answer_simple(question, [])
        
        prompt = f"""基于以下参考资料回答问题。如果资料不足以回答问题，请明确说明。

参考资料：
{context}

问题：{question}

请基于以上资料回答。回答时要注明信息来源。"""
        
        # TODO: 调用 LLM
        return "[LLM 回答功能待实现]"
    
    def _generate_answer_simple(self, question: str, sources: List[Dict]) -> str:
        """简单回答生成（无LLM时）"""
        if not sources:
            return "抱歉，我的知识库中没有相关信息。请自行搜集资料。"
        
        # 返回最相关的片段
        return f"根据知识库中的 {len(sources)} 条记录，相关内容如下：\n\n" + \
               "\n---\n".join(s['content'][:500] + "..." for s in sources[:3])
