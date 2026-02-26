# AI Note System

一个高度与 AI 融合的笔记系统，支持多模态内容管理和智能知识检索。

## ✨ 功能特性

### 📥 内容接入
- 网页链接抓取与解析
- PDF 文档文本提取
- Markdown 文件导入
- 图片 OCR 与内容理解

### 🧠 AI 处理
- **OpenAI 嵌入** (text-embedding-3-small)
- 自动文本分块与向量化
- 语义相似度搜索
- **LLM 智能回答** (GPT-4o-mini)

### 🔍 知识检索
- 自然语言问答（基于 LLM）
- **核心原则：无来源不回答**
- 相关度评分与来源追溯
- 相似内容推荐

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

```bash
export OPENAI_API_KEY='your-openai-api-key'
```

### 3. 启动 Web UI

```bash
python run_web.py
```

访问 http://127.0.0.1:8000

## 💻 使用示例

### Python API

```python
from main import create_system

# 创建系统
system = create_system()

# 上传网页
note = system.add_url("https://example.com/article")
print(f"Added: {note.title} ({len(note.vector_ids)} chunks)")

# 上传文件
note = system.add_pdf("./document.pdf")

# 知识问答
result = system.ask("这篇文章讲了什么？")
print(result['answer'])
# 输出: "根据参考资料[1]、[2]，这篇文章主要讲述了..."
```

## 🏗️ 系统架构

```
用户输入 → 内容处理器 → 文本提取 → 智能分块 → OpenAI嵌入 → ChromaDB存储
                                                          ↓
用户提问 → 查询向量化 → 向量相似搜索(Top-K) → LLM生成回答 ← 上下文构建
```

## 📁 项目结构

```
ai-note-system/
├── core/                   # 核心模块
│   ├── content_processor.py   # 内容处理主类
│   ├── embedding.py           # OpenAI 嵌入服务
│   ├── chunker.py             # 文本分块
│   ├── vector_store.py        # ChromaDB 向量存储
│   ├── query_engine.py        # 查询引擎 + LLM
│   └── llm.py                 # LLM 服务
├── connectors/             # 内容连接器
│   ├── web_fetcher.py
│   ├── pdf_parser.py
│   ├── markdown_parser.py
│   └── image_processor.py
├── ui/web/                 # Web 界面 (FastAPI)
├── data/                   # 数据存储
└── uploads/                # 上传文件
```

## ⚙️ 配置

复制 `.env.example` 为 `.env` 并填写：

```
OPENAI_API_KEY=your_key_here
```

## 📝 开发路线

- [x] v0.1 - 基础内容处理
- [x] v0.2 - 向量化与语义搜索
- [x] v0.3 - LLM 智能回答
- [ ] v0.4 - 知识图谱 (Neo4j)
- [ ] v0.5 - 对话历史与上下文
- [ ] v1.0 - 完整功能发布

## 📄 许可证

MIT License
