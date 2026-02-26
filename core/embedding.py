"""嵌入服务 - 管理文本向量化"""

from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class EmbeddingService:
    """文本嵌入服务"""
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化嵌入客户端"""
        if self.provider == "openai":
            try:
                from openai import OpenAI
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment")
                self._client = OpenAI(api_key=api_key)
                self.model = "text-embedding-3-small"
                self.dimension = 1536
            except ImportError:
                raise ImportError("Please install openai: pip install openai")
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        将文本列表转换为向量
        
        Args:
            texts: 文本列表
        
        Returns:
            向量列表
        """
        if not texts:
            return []
        
        # 过滤空文本
        texts = [t.strip() for t in texts if t and t.strip()]
        if not texts:
            return []
        
        if self.provider == "openai":
            return self._embed_openai(texts)
        
        return []
    
    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """使用 OpenAI API 嵌入"""
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Embedding error: {e}")
            # 返回零向量作为降级
            return [[0.0] * self.dimension for _ in texts]
    
    def embed_single(self, text: str) -> List[float]:
        """嵌入单个文本"""
        if not text or not text.strip():
            return [0.0] * self.dimension
        result = self.embed([text])
        return result[0] if result else [0.0] * self.dimension


# 全局嵌入服务实例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """获取全局嵌入服务实例"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
