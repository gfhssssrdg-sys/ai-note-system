"""文本分块 - 将长文本分割成适合向量化的片段"""

from typing import List, Optional
import re


class TextChunker:
    """文本分块器"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separator: str = "\n"
    ):
        """
        初始化分块器
        
        Args:
            chunk_size: 每个块的最大字符数
            chunk_overlap: 块之间的重叠字符数
            separator: 优先分隔符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
    
    def split(self, text: str) -> List[str]:
        """
        将文本分割成块
        
        Args:
            text: 原始文本
        
        Returns:
            文本块列表
        """
        if not text:
            return []
        
        # 如果文本长度小于块大小，直接返回
        if len(text) <= self.chunk_size:
            return [text.strip()] if text.strip() else []
        
        # 尝试按段落分割
        paragraphs = self._split_by_paragraphs(text)
        
        # 合并段落成块
        chunks = self._merge_paragraphs(paragraphs)
        
        return [c.strip() for c in chunks if c.strip()]
    
    def _split_by_paragraphs(self, text: str) -> List[str]:
        """按段落分割文本"""
        # 按多个换行符分割段落
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _merge_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """将段落合并成适当大小的块"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para_length = len(para)
            
            # 如果单个段落就超过块大小，需要进一步分割
            if para_length > self.chunk_size:
                # 先保存当前累积的内容
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))
                    # 保留重叠部分
                    overlap_text = self._get_overlap(current_chunk)
                    current_chunk = [overlap_text] if overlap_text else []
                    current_length = len(overlap_text)
                
                # 分割长段落
                sub_chunks = self._split_long_paragraph(para)
                chunks.extend(sub_chunks)
                continue
            
            # 检查添加这段后是否超过块大小
            new_length = current_length + para_length + len(self.separator)
            
            if new_length <= self.chunk_size:
                current_chunk.append(para)
                current_length = new_length
            else:
                # 保存当前块
                if current_chunk:
                    chunks.append(self.separator.join(current_chunk))
                
                # 保留重叠部分开始新块
                overlap_text = self._get_overlap(current_chunk)
                current_chunk = ([overlap_text] if overlap_text else []) + [para]
                current_length = sum(len(p) for p in current_chunk) + len(current_chunk) * len(self.separator)
        
        # 保存最后一个块
        if current_chunk:
            chunks.append(self.separator.join(current_chunk))
        
        return chunks
    
    def _split_long_paragraph(self, paragraph: str) -> List[str]:
        """分割长段落（按句子或固定长度）"""
        chunks = []
        
        # 尝试按句子分割
        sentences = re.split(r'(?<=[.!?。！？])\s+', paragraph)
        
        current_chunk = []
        current_length = 0
        
        for sent in sentences:
            sent_length = len(sent)
            
            if current_length + sent_length <= self.chunk_size:
                current_chunk.append(sent)
                current_length += sent_length
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                
                # 如果单个句子就超过限制，强制分割
                if sent_length > self.chunk_size:
                    for i in range(0, len(sent), self.chunk_size - self.chunk_overlap):
                        chunk = sent[i:i + self.chunk_size]
                        if chunk:
                            chunks.append(chunk)
                    current_chunk = []
                    current_length = 0
                else:
                    current_chunk = [sent]
                    current_length = sent_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def _get_overlap(self, chunks: List[str]) -> str:
        """获取与前一块的重叠文本"""
        if not chunks or self.chunk_overlap <= 0:
            return ""
        
        # 从最后一块取重叠部分
        last_chunk = chunks[-1]
        if len(last_chunk) <= self.chunk_overlap:
            return last_chunk
        
        return last_chunk[-self.chunk_overlap:]


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[str]:
    """
    快速分块函数
    
    Args:
        text: 要分割的文本
        chunk_size: 块大小
        chunk_overlap: 重叠大小
    
    Returns:
        文本块列表
    """
    chunker = TextChunker(chunk_size, chunk_overlap)
    return chunker.split(text)
