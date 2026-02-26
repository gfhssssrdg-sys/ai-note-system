"""FastAPI Web 应用"""

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import shutil
import os
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
    description="AI 融合的笔记系统 - 知识图谱版",
    version="0.4.0"
)

# 静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 模板
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# 目录设置
upload_dir = Path(__file__).parent.parent / "uploads"
upload_dir.mkdir(exist_ok=True)
data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(exist_ok=True)

# 初始化组件
vector_store = ChromaVectorStore(persist_dir=str(data_dir / "chroma"))
knowledge_graph = KnowledgeGraph()

# 初始化系统
system = NoteSystem(vector_store=vector_store, knowledge_graph=knowledge_graph)
system.register_processor(WebFetcher())
system.register_processor(PDFParser())
system.register_processor(MarkdownParser())
system.register_processor(ImageProcessor())

print(f"✓ System initialized: {vector_store.count()} vectors, Neo4j: {knowledge_graph.is_connected()}")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    stats = system.get_stats()
    return templates.TemplateResponse("index.html", {"request": request, "stats": stats})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/notes", response_class=HTMLResponse)
async def notes_page(request: Request):
    notes = system.list_notes()
    return templates.TemplateResponse("notes.html", {"request": request, "notes": notes})


@app.get("/note/{note_id}", response_class=HTMLResponse)
async def note_detail(request: Request, note_id: str):
    note = system.get_note(note_id)
    if not note:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse("note_detail.html", {"request": request, "note": note})


@app.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request):
    return templates.TemplateResponse("ask.html", {"request": request})


@app.get("/graph", response_class=HTMLResponse)
async def graph_page(request: Request):
    """知识图谱可视化页面"""
    return templates.TemplateResponse("graph.html", {"request": request})


# API Endpoints

@app.post("/api/upload/url")
async def upload_url(url: str = Form(...)):
    try:
        note = system.add_url(url)
        return JSONResponse({
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "type": note.source_type,
                "vector_chunks": len(note.vector_ids),
                "entities": len(note.entities),
                "relations": len(note.relations)
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.post("/api/upload/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = upload_dir / file.filename
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        
        note = system.add_content(str(file_path))
        
        return JSONResponse({
            "success": True,
            "note": {
                "id": note.id,
                "title": note.title,
                "type": note.source_type,
                "vector_chunks": len(note.vector_ids),
                "entities": len(note.entities),
                "relations": len(note.relations)
            }
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@app.get("/api/notes")
async def get_notes():
    notes = system.list_notes()
    return {
        "notes": [
            {
                "id": n.id,
                "title": n.title or "Untitled",
                "type": n.source_type,
                "entities": len(n.entities),
                "relations": len(n.relations),
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notes
        ]
    }


@app.get("/api/stats")
async def get_stats():
    return system.get_stats()


@app.post("/api/ask")
async def ask_question(question: str = Form(...)):
    try:
        from core.llm import get_llm_service
        result = system.ask(question)
        return JSONResponse({
            "success": True,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "confidence": result.get("confidence", 0),
            "has_sufficient_sources": result.get("has_sufficient_sources", False),
            "source_chunks": result.get("source_chunks", [])
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/search")
async def search_notes(q: str):
    if not vector_store:
        return {"results": []}
    try:
        results = vector_store.search(q, top_k=10)
        return {
            "results": [
                {
                    "note_id": r["note_id"],
                    "title": r.get("title", "Untitled"),
                    "content": r["content"][:200] + "...",
                    "similarity": r["similarity"]
                }
                for r in results
            ]
        }
    except Exception as e:
        return {"results": [], "error": str(e)}


# 知识图谱 API

@app.get("/api/graph/entities")
async def get_entities(limit: int = 100):
    """获取所有实体"""
    entities = knowledge_graph.get_all_entities(limit=limit)
    return {"entities": entities}


@app.get("/api/graph/network")
async def get_network(name: str, depth: int = 2):
    """获取实体的关系网络"""
    network = knowledge_graph.get_entity_network(name, depth=depth)
    return network


@app.get("/api/graph/path")
async def find_path(from_entity: str, to_entity: str, max_depth: int = 4):
    """查找两个实体间的路径"""
    paths = knowledge_graph.find_path(from_entity, to_entity, max_depth)
    return {"paths": paths}


@app.get("/api/graph/stats")
async def get_graph_stats():
    """获取图谱统计"""
    return knowledge_graph.get_stats()


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: str):
    try:
        success = system.delete_note(note_id)
        return JSONResponse({"success": success})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
