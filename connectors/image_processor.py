"""图片处理器 - OCR 和内容理解"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import io

from core.content_processor import ContentProcessor, ContentItem


class ImageProcessor(ContentProcessor):
    """图片内容处理器"""
    
    SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff')
    
    def __init__(self, ocr_enabled: bool = True):
        self.ocr_enabled = ocr_enabled
    
    def can_process(self, source: str) -> bool:
        """检查是否为支持的图片格式"""
        return source.lower().endswith(self.SUPPORTED_FORMATS)
    
    def process(self, source: str) -> ContentItem:
        """处理图片文件"""
        file_path = Path(source)
        
        # 打开图片
        image = Image.open(source)
        
        # 获取图片信息
        metadata = self._extract_metadata(image, file_path)
        
        # OCR 提取文本
        ocr_text = ""
        if self.ocr_enabled:
            ocr_text = self._perform_ocr(image)
        
        # 图片描述（可由 AI 生成）
        description = ""
        
        # 合并内容
        content_parts = []
        if description:
            content_parts.append(f"图片描述: {description}")
        if ocr_text:
            content_parts.append(f"图片中的文字:\n{ocr_text}")
        
        content = "\n\n".join(content_parts) if content_parts else "[图片]"
        
        # 保存图片数据
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=image.format or 'PNG')
        raw_content = img_bytes.getvalue()
        
        # 创建 ContentItem
        item = ContentItem(
            id="",
            source_type="image",
            source_path=str(file_path.absolute()),
            title=file_path.stem,
            content=content,
            raw_content=raw_content,
            metadata=metadata
        )
        item.id = item.generate_id()
        
        return item
    
    def extract_text(self, content_item: ContentItem) -> str:
        """提取 OCR 文本"""
        return content_item.content or ""
    
    def _extract_metadata(self, image: Image.Image, file_path: Path) -> Dict[str, Any]:
        """提取图片元数据"""
        metadata = {
            'filename': file_path.name,
            'format': image.format,
            'mode': image.mode,
            'width': image.width,
            'height': image.height,
            'file_size': file_path.stat().st_size,
        }
        
        # EXIF 数据（如果有）
        if hasattr(image, '_getexif') and image._getexif():
            exif = image._getexif()
            exif_data = {}
            for tag_id, value in exif.items():
                # 常见 EXIF 标签
                if tag_id == 36867:  # DateTimeOriginal
                    exif_data['date_taken'] = value
                elif tag_id == 272:  # Model
                    exif_data['camera'] = value
                elif tag_id == 33432:  # Copyright
                    exif_data['copyright'] = value
            if exif_data:
                metadata['exif'] = exif_data
        
        return metadata
    
    def _perform_ocr(self, image: Image.Image) -> str:
        """执行 OCR 识别"""
        try:
            import pytesseract
            
            # 预处理：转为灰度
            if image.mode != 'L':
                image = image.convert('L')
            
            # 执行 OCR
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            
            # 清理文本
            text = text.strip()
            
            return text
        except ImportError:
            return "[OCR 需要安装 pytesseract: pip install pytesseract]"
        except Exception as e:
            return f"[OCR 失败: {str(e)}]"
    
    def generate_thumbnail(self, source: str, max_size: tuple = (300, 300)) -> bytes:
        """生成缩略图"""
        image = Image.open(source)
        image.thumbnail(max_size)
        
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        return img_bytes.getvalue()
