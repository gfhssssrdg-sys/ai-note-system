"""向量存储 - 管理内容的向量表示和语义检索"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib


@dataclass
class VectorRecord:
    """向量记录"""
    id: str
    note_id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]


class VectorStore:
    """向量存储抽象类"""
    
    def __init__(self, collection_name: str = "notes"):
        self.collection_name = collection_name
    
    def add(self, records: List[VectorRecord]) -> bool:
        """添加向量记录"""
        raise NotImplementedError
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """语义搜索"""
        raise NotImplementedError
    
    def delete(self, note_id: str) -> bool:
        """删除笔记的向量记录"""
        raise NotImplementedError
    
    def get_related(self, note_id: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取相关笔记"""
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    """基于 ChromaDB 的向量存储"""
    
    def __init__(self, persist_dir: str = "./data/chroma", **kwargs):
        super().__init__(**kwargs)
        self.persist_dir = persist_dir
        self._init_chroma()
    
    def _init_chroma(self):
        """初始化 ChromaDB"""
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
        except ImportError:
            raise ImportError("Please install chromadb: pip install chromadb")
    
    def add(self, records: List[VectorRecord]) -> bool:
        """添加向量记录"""
        if not records:
            return True
        
        ids = [r.id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.content for r in records]
        metadatas = [r.metadata for r in records]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        return True
    
    def search(
        self, 
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict
        )
        
        matches = []
        for i in range(len(results['ids'][0])):
            matches.append({
                'id': results['ids'][0][i],
                'note_id': results['metadatas'][0][i].get('note_id'),
                'content': results['documents'][0][i],
                'distance': results['distances'][0][i],
                'metadata': results['metadatas'][0][i]
            })
        
        return matches
    
    def delete(self, note_id: str) -> bool:
        """删除笔记的所有向量片段"""
        self.collection.delete(where={"note_id": note_id})
        return True
