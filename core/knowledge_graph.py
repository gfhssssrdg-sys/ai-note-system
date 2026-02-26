"""知识图谱 - 管理笔记间的实体关系和语义连接"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class Entity:
    """知识图谱中的实体"""
    id: str
    name: str
    entity_type: str  # person, organization, concept, etc.
    source_notes: List[str]  # 来源笔记ID
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class Relation:
    """实体间的关系"""
    source_id: str
    target_id: str
    relation_type: str  # related_to, mentions, contains, etc.
    weight: float = 1.0
    source_notes: List[str] = None
    
    def __post_init__(self):
        if self.source_notes is None:
            self.source_notes = []


class KnowledgeGraph:
    """知识图谱管理"""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        self._init_connection()
    
    def _init_connection(self):
        """初始化数据库连接"""
        if self.uri:
            try:
                from neo4j import GraphDatabase
                self.driver = GraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
            except ImportError:
                pass  # 降级为内存模式
    
    def add_entities(self, entities: List[Entity]) -> bool:
        """批量添加实体"""
        if self.driver:
            return self._add_entities_neo4j(entities)
        else:
            return self._add_entities_memory(entities)
    
    def add_relations(self, relations: List[Relation]) -> bool:
        """批量添加关系"""
        if self.driver:
            return self._add_relations_neo4j(relations)
        else:
            return self._add_relations_memory(relations)
    
    def find_path(self, start_entity: str, end_entity: str, max_depth: int = 3) -> List[List[Relation]]:
        """查找两个实体间的关联路径"""
        # TODO: 实现路径查找
        return []
    
    def get_related_entities(self, entity_id: str, relation_type: str = None) -> List[Entity]:
        """获取相关实体"""
        # TODO: 实现相关实体查询
        return []
    
    def build_from_note(self, note_id: str, content: str, entities: List[str]) -> Tuple[List[Entity], List[Relation]]:
        """
        从笔记内容构建知识图谱
        
        Args:
            note_id: 笔记ID
            content: 笔记内容
            entities: 提取的实体列表
        
        Returns:
            (实体列表, 关系列表)
        """
        # TODO: 使用 LLM 提取实体和关系
        return [], []
    
    # Neo4j 实现
    def _add_entities_neo4j(self, entities: List[Entity]) -> bool:
        with self.driver.session() as session:
            for entity in entities:
                session.run("""
                    MERGE (e:Entity {id: $id})
                    SET e.name = $name,
                        e.type = $type,
                        e.properties = $properties
                    WITH e
                    UNWIND $source_notes as note_id
                    MERGE (n:Note {id: note_id})
                    MERGE (e)<-[:MENTIONS]-(n)
                """, {
                    "id": entity.id,
                    "name": entity.name,
                    "type": entity.entity_type,
                    "properties": json.dumps(entity.properties),
                    "source_notes": entity.source_notes
                })
        return True
    
    def _add_relations_neo4j(self, relations: List[Relation]) -> bool:
        with self.driver.session() as session:
            for rel in relations:
                session.run("""
                    MATCH (s:Entity {id: $source})
                    MATCH (t:Entity {id: $target})
                    MERGE (s)-[r:RELATES {type: $type}]->(t)
                    SET r.weight = $weight
                """, {
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relation_type,
                    "weight": rel.weight
                })
        return True
    
    # 内存实现（降级模式）
    def _add_entities_memory(self, entities: List[Entity]) -> bool:
        # TODO: 实现内存版
        return True
    
    def _add_relations_memory(self, relations: List[Relation]) -> bool:
        # TODO: 实现内存版
        return True
