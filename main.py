"""AI Note System - 主入口"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.content_processor import NoteSystem
from core.vector_store import ChromaVectorStore
from core.knowledge_graph import KnowledgeGraph
from core.query_engine import QueryEngine
from connectors.web_fetcher import WebFetcher
from connectors.pdf_parser import PDFParser
from connectors.markdown_parser import MarkdownParser
from connectors.image_processor import ImageProcessor


def create_system():
    """创建并配置笔记系统"""
    system = NoteSystem()
    
    # 注册内容处理器
    system.register_processor(WebFetcher())
    system.register_processor(PDFParser())
    system.register_processor(MarkdownParser())
    system.register_processor(ImageProcessor())
    
    return system


def main():
    """主函数"""
    print("=" * 50)
    print("AI Note System v0.1.0")
    print("=" * 50)
    
    # 创建系统
    system = create_system()
    
    print("\n内容处理器已加载:")
    for i, processor in enumerate(system.processors, 1):
        print(f"  {i}. {processor.__class__.__name__}")
    
    print("\n系统已就绪！")
    print("\n使用示例:")
    print('  from main import create_system')
    print('  system = create_system()')
    print('  note = system.add_url("https://example.com")')
    print('  answer = system.ask("你的问题")')


if __name__ == "__main__":
    main()
