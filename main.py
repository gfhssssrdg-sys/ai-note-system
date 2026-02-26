"""AI Note System - 主入口"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.content_processor import NoteSystem
from core.vector_store import ChromaVectorStore
from core.knowledge_graph import KnowledgeGraph
from connectors.web_fetcher import WebFetcher
from connectors.pdf_parser import PDFParser
from connectors.markdown_parser import MarkdownParser
from connectors.image_processor import ImageProcessor


def create_system(data_dir: str = "./data") -> NoteSystem:
    """创建并配置笔记系统"""
    
    data_path = Path(data_dir)
    data_path.mkdir(exist_ok=True)
    
    # 初始化组件
    print("Initializing components...")
    vector_store = ChromaVectorStore(persist_dir=str(data_path / "chroma"))
    knowledge_graph = KnowledgeGraph()
    
    # 创建系统
    system = NoteSystem(vector_store=vector_store, knowledge_graph=knowledge_graph)
    
    # 注册处理器
    system.register_processor(WebFetcher())
    system.register_processor(PDFParser())
    system.register_processor(MarkdownParser())
    system.register_processor(ImageProcessor())
    
    return system


def check_services():
    """检查服务状态"""
    checks = {
        "OpenAI API": bool(os.getenv("OPENAI_API_KEY")),
        "Neo4j": bool(os.getenv("NEO4J_PASSWORD"))
    }
    return checks


def main():
    """主函数"""
    print("=" * 60)
    print("🧠 AI Note System v0.4.0 - 知识图谱版")
    print("=" * 60)
    
    # 检查服务
    services = check_services()
    
    # 创建系统
    system = create_system()
    
    # 显示状态
    print("\n✓ System initialized")
    print(f"  Content processors: {len(system.processors)}")
    
    stats = system.get_stats()
    print(f"  Notes in memory: {stats['total_notes']}")
    print(f"  Vector chunks: {stats['vector_count']}")
    
    if stats.get('graph_stats'):
        gs = stats['graph_stats']
        print(f"  Knowledge Graph: {gs.get('entities', 0)} entities, {gs.get('relations', 0)} relations")
    
    print("\nServices:")
    for name, status in services.items():
        print(f"  {'✓' if status else '✗'} {name}")
    
    print("\nUsage:")
    print('  from main import create_system')
    print('  system = create_system()')
    print('  note = system.add_url("https://example.com")')
    print('  result = system.ask("你的问题")')
    print()
    print("Start Web UI:")
    print('  python run_web.py')
    print()
    print("Then open: http://127.0.0.1:8000")
    print("=" * 60)


if __name__ == "__main__":
    main()
