"""实体提取 - 从文本中提取实体和关系"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from core.llm import LLMService, get_llm_service
import json


@dataclass
class Entity:
    """知识图谱中的实体"""
    id: str
    name: str
    entity_type: str  # person, organization, concept, location, etc.
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class Relation:
    """实体间的关系"""
    source: str  # 源实体名称
    target: str  # 目标实体名称
    relation_type: str  # 关系类型
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class EntityExtractor:
    """实体和关系提取器"""
    
    # 实体类型定义
    ENTITY_TYPES = {
        "person": "人物",
        "organization": "组织",
        "concept": "概念",
        "technology": "技术",
        "location": "地点",
        "product": "产品",
        "event": "事件",
        "field": "领域"
    }
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()
    
    def extract(self, text: str, note_id: str, title: str = None) -> Dict[str, List]:
        """
        从文本中提取实体和关系
        
        Args:
            text: 文本内容
            note_id: 笔记ID
            title: 笔记标题
        
        Returns:
            {"entities": [...], "relations": [...]}
        """
        if not text or len(text.strip()) < 50:
            return {"entities": [], "relations": []}
        
        # 截取前 3000 字符（控制成本）
        truncated_text = text[:3000]
        
        prompt = f"""请从以下文本中提取知识图谱实体和关系。

文本标题: {title or '无标题'}

文本内容:
{truncated_text}

请提取:
1. 重要实体（最多10个）：人物、组织、概念、技术、产品等
2. 实体间的关系（最多15个）

输出 JSON 格式:
{{
    "entities": [
        {{"name": "实体名称", "type": "person/organization/concept/technology/product/location/event/field", "description": "简要描述"}}
    ],
    "relations": [
        {{"source": "源实体", "target": "目标实体", "type": "关系类型", "description": "关系描述"}}
    ]
}}

要求:
- 只提取文本中明确提到的实体和关系
- 实体名称为文本中出现的原文
- 关系类型用简短的动词或动词短语，如"属于"、"创建"、"使用"、"位于"等"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的知识图谱构建助手，擅长从文本中提取实体和关系。只输出 JSON 格式。"},
                {"role": "user", "content": prompt}
            ]
            
            response = self.llm.complete(messages)
            
            # 解析 JSON
            result = self._parse_json(response)
            
            # 转换为对象
            entities = [
                Entity(
                    id=self._entity_id(e["name"]),
                    name=e["name"],
                    entity_type=e.get("type", "concept"),
                    properties={
                        "description": e.get("description", ""),
                        "note_id": note_id,
                        "note_title": title
                    }
                )
                for e in result.get("entities", [])
            ]
            
            relations = [
                Relation(
                    source=r["source"],
                    target=r["target"],
                    relation_type=r.get("type", "相关"),
                    properties={
                        "description": r.get("description", ""),
                        "note_id": note_id
                    }
                )
                for r in result.get("relations", [])
            ]
            
            return {"entities": entities, "relations": relations}
            
        except Exception as e:
            print(f"Entity extraction failed: {e}")
            return {"entities": [], "relations": []}
    
    def _parse_json(self, text: str) -> Dict:
        """解析 JSON，处理可能的格式问题"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # 返回空结果
        return {"entities": [], "relations": []}
    
    def _entity_id(self, name: str) -> str:
        """生成实体 ID"""
        import hashlib
        return hashlib.md5(name.encode()).hexdigest()[:12]


def extract_from_note(note, llm_service: Optional[LLMService] = None) -> Dict[str, List]:
    """
    从笔记中提取实体和关系的便捷函数
    
    Args:
        note: ContentItem 对象
        llm_service: LLM 服务实例
    
    Returns:
        {"entities": [...], "relations": [...]}
    """
    extractor = EntityExtractor(llm_service)
    return extractor.extract(
        text=note.content or "",
        note_id=note.id,
        title=note.title
    )
