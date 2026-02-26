#!/usr/bin/env python3
"""Web UI 启动脚本"""

import sys
from pathlib import Path

# 确保在项目目录
project_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_dir))

from ui.web.app import app
import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("🧠 AI Note System - Web UI")
    print("=" * 50)
    print()
    print("启动服务器...")
    print()
    print("访问地址:")
    print("  - 本地: http://127.0.0.1:8000")
    print("  - 局域网: http://0.0.0.0:8000")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
