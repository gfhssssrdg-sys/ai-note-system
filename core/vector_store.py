"""向量存储 - 管理内容的向量表示和语义检索"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json

from core.embedding import get_embedding_service, EmbeddingService
from core.chunker import chunk_text


@dataclass
class VectorRecord:
    """向量记录"""
    id: str
    note_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    chunk_index: int = 0  # 在笔记中的块序号


class VectorStore:
    """向量存储抽象类"""
    
    def __init__(self, collection_name: str = "notes"):
        self.collection_name = collection_name
        self.embedding_service = get_embedding_service()
    
    def add_note(self, note_id: str, title: str, content: str, metadata: Dict = None) -> List[str]:
        """
        添加笔记到向量存储（自动分块和嵌入）
        
        Args:
            note_id: 笔记ID
            title: 笔记标题
            content: 笔记内容
            metadata: 额外元数据
        
        Returns:
            向量记录ID列表
        """
        if not content or not content.strip():
            return []
        
        # 文本分块
        chunks = chunk_text(content, chunk_size=500, chunk_overlap=50)
        
        if not chunks:
            return []
        
        # 为每个块生成向量记录
        records = []
        for i, chunk in enumerate(chunks):
            # 构造带标题的上下文
            chunk_with_context = f"{title}\n\n{chunk}" if title else chunk
            
            # 生成嵌入
            embedding = self.embedding_service.embed_single(chunk_with_context)
            
            # 生成唯一ID
            chunk_id = f"{note_id}_chunk_{i}"
            
            record = VectorRecord(
                id=chunk_id,
                note_id=note_id,
                content=chunk,
                embedding=embedding,
                metadata={
                    **(metadata or {}),
                    "title": title,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                },
                chunk_index=i
            )
            records.append(record)
        
        # 批量添加
        self._add_records(records)
        
        return [r.id for r in records]
    
    def _add_records(self, records: List[VectorRecord]) -> bool:
        """批量添加向量记录（子类实现）"""
        raise NotImplementedError
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件
        
        Returns:
            搜索结果列表
        """
        # 将查询转为向量
        query_embedding = self.embedding_service.embed_single(query)
        
        # 执行向量搜索
        return self._search_vectors(query_embedding, top_k, filter_dict)
    
    def _search_vectors(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_dict: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """向量搜索（子类实现）"""
        raise NotImplementedError
    
    def delete(self, note_id: str) -> bool:
        """删除笔记的所有向量片段"""
        raise NotImplementedError
    
    def get_related(self, note_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取相关笔记"""
        # TODO: 获取笔记的代表性向量，搜索相似内容
        return []


class ChromaVectorStore(VectorStore):
    """基于 ChromaDB 的向量存储"""
    
    def __init__(self, persist_dir: str = "./data/chroma", **kwargs):
        self.persist_dir = persist_dir
        self._client = None
        self._collection = None
        super().__init__(**kwargs)
        self._init_chroma()
    
    def _init_chroma(self):
        """初始化 ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(
                    anonymized_telemetry=False
                )
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✓ ChromaDB initialized at {self.persist_dir}")
        except ImportError:
            raise ImportError("Please install chromadb: pip install chromadb")
    
    def _add_records(self, records: List[VectorRecord]) -> bool:
        """批量添加向量记录"""
        if not records:
            return True
        
        ids = [r.id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.content for r in records]
        metadatas = [r.metadata for r in records]
        
        # 添加 note_id 到 metadata
        for i, r in enumerate(records):
            metadatas[i]["note_id"] = r.note_id
        
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return True
    
    def _search_vectors(
        self,
        query_embedding: List[float],
        top_k: int,
        filter_dict: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        matches = []
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i]
            # Chroma 返回的是距离，转换为相似度分数
            # cosine 距离范围 [0, 2]，转换为 [0, 1] 相似度
            similarity = 1 - (distance / 2)
            
            matches.append({
                'id': results['ids'][0][i],
                'note_id': results['metadatas'][0][i].get('note_id'),
                'content': results['documents'][0][i],
                'title': results['metadatas'][0][i].get('title'),
                'distance': distance,
                'similarity': similarity,
                'metadata': results['metadatas'][0][i]
            })
        
        return matches
    
    def delete(self, note_id: str) -> bool:
        """删除笔记的所有向量片段"""
        self._collection.delete(where={"note_id": note_id})
        return True
    
    def count(self) -> int:
        """获取向量记录总数"""
        return self._collection.count()
