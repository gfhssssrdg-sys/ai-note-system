"""PDF 解析器 - 提取 PDF 文本和元数据"""

import fitz  # PyMuPDF
from typing import Optional, List, Dict, Any
from pathlib import Path

from core.content_processor import ContentProcessor, ContentItem


class PDFParser(ContentProcessor):
    """PDF 文档处理器"""
    
    def __init__(self, extract_images: bool = False, ocr_enabled: bool = False):
        self.extract_images = extract_images
        self.ocr_enabled = ocr_enabled
    
    def can_process(self, source: str) -> bool:
        """检查是否为 PDF 文件"""
        return source.lower().endswith('.pdf')
    
    def process(self, source: str) -> ContentItem:
        """解析 PDF 文件"""
        file_path = Path(source)
        
        # 打开 PDF
        doc = fitz.open(source)
        
        # 提取文本
        full_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            full_text.append(f"--- Page {page_num + 1} ---\n{text}")
        
        content = "\n\n".join(full_text)
        
        # 提取元数据
        metadata = self._extract_metadata(doc, file_path)
        
        # 提取大纲/目录
        toc = doc.get_toc()
        if toc:
            metadata['table_of_contents'] = toc
        
        # 关闭文档
        doc.close()
        
        # 创建 ContentItem
        item = ContentItem(
            id="",
            source_type="pdf",
            source_path=str(file_path.absolute()),
            title=metadata.get('title') or file_path.stem,
            content=content,
            raw_content=None,
            metadata=metadata
        )
        item.id = item.generate_id()
        
        return item
    
    def extract_text(self, content_item: ContentItem) -> str:
        """提取纯文本"""
        return content_item.content or ""
    
    def _extract_metadata(self, doc: fitz.Document, file_path: Path) -> Dict[str, Any]:
        """提取 PDF 元数据"""
        pdf_metadata = doc.metadata
        
        metadata = {
            'filename': file_path.name,
            'file_size': file_path.stat().st_size,
            'page_count': len(doc),
            'format': 'PDF',
        }
        
        # PDF 标准元数据
        if pdf_metadata:
            metadata.update({
                'title': pdf_metadata.get('title'),
                'author': pdf_metadata.get('author'),
                'subject': pdf_metadata.get('subject'),
                'creator': pdf_metadata.get('creator'),
                'producer': pdf_metadata.get('producer'),
                'creation_date': pdf_metadata.get('creationDate'),
                'modification_date': pdf_metadata.get('modDate'),
            })
        
        return {k: v for k, v in metadata.items() if v is not None}
    
    def extract_images(self, source: str, output_dir: str = None) -> List[Dict[str, Any]]:
        """提取 PDF 中的图片（可选功能）"""
        if not self.extract_images:
            return []
        
        doc = fitz.open(source)
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                images.append({
                    'page': page_num + 1,
                    'index': img_index,
                    'format': image_ext,
                    'size': len(image_bytes),
                    'data': image_bytes
                })
        
        doc.close()
        return images
