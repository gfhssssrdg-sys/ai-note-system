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


def create_system(data_dir: str = "./data") -> NoteSystem:
    """创建并配置笔记系统"""
    
    # 确保数据目录存在
    data_path = Path(data_dir)
    data_path.mkdir(exist_ok=True)
    
    # 初始化向量存储
    print(f"Initializing vector store at {data_path / 'chroma'}...")
    vector_store = ChromaVectorStore(persist_dir=str(data_path / "chroma"))
    
    # 创建系统
    system = NoteSystem(vector_store=vector_store)
    
    # 注册内容处理器
    system.register_processor(WebFetcher())
    system.register_processor(PDFParser())
    system.register_processor(MarkdownParser())
    system.register_processor(ImageProcessor())
    
    return system


def main():
    """主函数"""
    print("=" * 50)
    print("🧠 AI Note System v0.2.0")
    print("=" * 50)
    
    # 检查 API 密钥
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  Warning: OPENAI_API_KEY not set in environment")
        print("   Vectorization will not work without it.")
        print("   Set it with: export OPENAI_API_KEY='your-key'")
    
    # 创建系统
    system = create_system()
    
    print("\n✓ System initialized")
    print(f"  - Content processors: {len(system.processors)}")
    
    stats = system.get_stats()
    print(f"  - Notes in memory: {stats['total_notes']}")
    print(f"  - Vectors in database: {stats['vector_count']}")
    
    print("\n使用示例:")
    print('  from main import create_system')
    print('  system = create_system()')
    print('  note = system.add_url("https://example.com")')
    print('  result = system.ask("你的问题")')
    print()
    print("启动 Web UI:")
    print('  python run_web.py')


if __name__ == "__main__":
    main()
