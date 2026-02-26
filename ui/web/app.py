"""FastAPI Web 应用"""

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import tempfile
from typing import List, Optional
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.content_processor import NoteSystem
from core.vector_store import ChromaVectorStore
from core.knowledge_graph import KnowledgeGraph
from core.query_engine import QueryEngine
from connectors.web_fetcher import WebFetcher
from connectors.pdf_parser import PDFParser
from connectors.markdown_parser import MarkdownParser
from connectors.image_processor import ImageProcessor


app = FastAPI(
    title="AI Note System",
    description="AI 融合的笔记系统",
    version="0.1.0"
)

# 静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 模板
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# 上传目录
upload_dir = Path(__file__).parent.parent / "uploads"
upload_dir.mkdir(exist_ok=True)

# 初始化系统
system = NoteSystem()
system.register_processor(WebFetcher())
system.register_processor(PDFParser())
system.register_processor(MarkdownParser())
system.register_processor(ImageProcessor())


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """上传页面"""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/api/upload/url")
async def upload_url(url: str = Form(...)):
    """上传网页链接"""
    try:
        note = system.add_url(url)
        return JSONResponse({
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "type": note.source_type,
                "content_preview": note.content[:500] + "..." if len(note.content) > 500 else note.content
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/upload/file")
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    try:
        # 保存文件
        file_path = upload_dir / file.filename
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # 处理文件
        note = system.add_content(str(file_path))
        
        return JSONResponse({
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "type": note.source_type,
                "content_preview": note.content[:500] + "..." if len(note.content) > 500 else note.content
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    """笔记列表页面"""
    notes = system.list_notes()
    return templates.TemplateResponse("notes.html", {
        "request": request,
        "notes": notes
    })


@app.get("/api/notes")
async def get_notes():
    """获取所有笔记 API"""
    notes = system.list_notes()
    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title or "Untitled",
                "type": n.source_type,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notes
        ]
    }


@app.get("/note/{note_id}", response_class=HTMLResponse)
async def note_detail(request: Request, note_id: str):
    """笔记详情页面"""
    note = system.get_note(note_id)
    if not note:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    
    return templates.TemplateResponse("note_detail.html", {
        "request": request,
        "note": note
    })


@app.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request):
    """问答页面"""
    return templates.TemplateResponse("ask.html", {"request": request})


@app.post("/api/ask")
async def ask_question(question: str = Form(...)):
    """提问 API"""
    try:
        result = system.ask(question)
        return JSONResponse({
            "success": True,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0),
            "has_sufficient_sources": result.get("has_sufficient_sources", False)
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/search")
async def search_notes(q: str):
    """搜索笔记"""
    notes = system.list_notes()
    results = []
    query_lower = q.lower()
    
    for note in notes:
        if (query_lower in (note.title or "").lower() or 
            query_lower in (note.content or "").lower()):
            results.append({
                "id": note.id,
                "title": note.title or "Untitled",
                "type": note.source_type,
                "preview": note.content[:200] + "..." if len(note.content) > 200 else note.content
            })
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
