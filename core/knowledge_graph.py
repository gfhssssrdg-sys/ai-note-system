"""知识图谱 - 管理笔记间的实体关系和语义连接"""

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import os
from dotenv import load_dotenv

from core.entity_extraction import Entity, Relation

load_dotenv()


class KnowledgeGraph:
    """知识图谱管理 - Neo4j 实现"""
    
    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None
    ):
        """
        初始化知识图谱
        
        Args:
            uri: Neo4j 连接地址，默认 bolt://localhost:7687
            user: 用户名，默认 neo4j
            password: 密码，从环境变量获取
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.driver = None
        
        if self.password:
            self._init_connection()
        else:
            print("⚠️ Neo4j password not set, running in offline mode")
    
    def _init_connection(self):
        """初始化数据库连接"""
        try:
            from neo4j import GraphDatabase
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                result.single()
            print(f"✓ Connected to Neo4j at {self.uri}")
        except ImportError:
            print("⚠️ neo4j package not installed, running in offline mode")
        except Exception as e:
            print(f"⚠️ Neo4j connection failed: {e}, running in offline mode")
            self.driver = None
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.driver is not None
    
    def add_note_with_entities(
        self,
        note_id: str,
        note_title: str,
        entities: List[Entity],
        relations: List[Relation]
    ) -> bool:
        """
        添加笔记及其实体关系到图谱
        
        Args:
            note_id: 笔记ID
            note_title: 笔记标题
            entities: 实体列表
            relations: 关系列表
        
        Returns:
            是否成功
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # 1. 创建笔记节点
                session.run("""
                    MERGE (n:Note {id: $note_id})
                    SET n.title = $title,
                        n.updated_at = datetime()
                """, {"note_id": note_id, "title": note_title})
                
                # 2. 创建实体节点并关联到笔记
                for entity in entities:
                    session.run("""
                        MERGE (e:Entity {id: $entity_id})
                        SET e.name = $name,
                            e.type = $type,
                            e.description = $description
                        WITH e
                        MATCH (n:Note {id: $note_id})
                        MERGE (n)-[:CONTAINS]->(e)
                    """, {
                        "entity_id": entity.id,
                        "name": entity.name,
                        "type": entity.entity_type,
                        "description": entity.properties.get("description", ""),
                        "note_id": note_id
                    })
                
                # 3. 创建实体间的关系
                for rel in relations:
                    # 查找源实体和目标实体的 ID
                    source_id = self._find_entity_id(entities, rel.source)
                    target_id = self._find_entity_id(entities, rel.target)
                    
                    if source_id and target_id:
                        session.run("""
                            MATCH (s:Entity {id: $source_id})
                            MATCH (t:Entity {id: $target_id})
                            MERGE (s)-[r:RELATES {type: $rel_type}]->(t)
                            SET r.description = $description,
                                r.note_id = $note_id
                        """, {
                            "source_id": source_id,
                            "target_id": target_id,
                            "rel_type": rel.relation_type,
                            "description": rel.properties.get("description", ""),
                            "note_id": note_id
                        })
            
            print(f"✓ Added {len(entities)} entities, {len(relations)} relations for note {note_id[:8]}...")
            return True
            
        except Exception as e:
            print(f"Failed to add to knowledge graph: {e}")
            return False
    
    def _find_entity_id(self, entities: List[Entity], name: str) -> Optional[str]:
        """在实体列表中查找名称匹配的实体 ID"""
        for e in entities:
            if e.name == name or name in e.name or e.name in name:
                return e.id
        return None
    
    def get_entity_network(self, entity_name: str, depth: int = 2) -> Dict:
        """
        获取实体的关系网络
        
        Args:
            entity_name: 实体名称
            depth: 关系深度
        
        Returns:
            网络数据 {"nodes": [...], "links": [...]}
        """
        if not self.driver:
            return {"nodes": [], "links": []}
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (center:Entity {name: $name})-[:RELATES*1..$depth]-(connected)
                    RETURN center, connected, relationships(path) as rels
                    LIMIT 50
                """, {"name": entity_name, "depth": depth})
                
                nodes = {}
                links = []
                
                for record in result:
                    center = record["center"]
                    connected = record["connected"]
                    rels = record["rels"]
                    
                    # 添加节点
                    nodes[center["id"]] = {
                        "id": center["id"],
                        "name": center["name"],
                        "type": center.get("type", "unknown")
                    }
                    nodes[connected["id"]] = {
                        "id": connected["id"],
                        "name": connected["name"],
                        "type": connected.get("type", "unknown")
                    }
                    
                    # 添加关系
                    for rel in rels:
                        links.append({
                            "source": rel.start_node["id"],
                            "target": rel.end_node["id"],
                            "type": rel.get("type", "相关")
                        })
                
                return {
                    "nodes": list(nodes.values()),
                    "links": links
                }
        except Exception as e:
            print(f"Failed to get network: {e}")
            return {"nodes": [], "links": []}
    
    def get_all_entities(self, limit: int = 100) -> List[Dict]:
        """获取所有实体"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity)
                    RETURN e.id as id, e.name as name, e.type as type
                    LIMIT $limit
                """, {"limit": limit})
                
                return [dict(record) for record in result]
        except Exception as e:
            print(f"Failed to get entities: {e}")
            return []
    
    def find_path(self, from_entity: str, to_entity: str, max_depth: int = 4) -> List[Dict]:
        """
        查找两个实体间的路径
        
        Args:
            from_entity: 起始实体名称
            to_entity: 目标实体名称
            max_depth: 最大深度
        
        Returns:
            路径列表
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = shortestPath(
                        (a:Entity {name: $from})-[:RELATES*1..$depth]-(b:Entity {name: $to})
                    )
                    RETURN path
                """, {"from": from_entity, "to": to_entity, "depth": max_depth})
                
                paths = []
                for record in result:
                    path = record["path"]
                    nodes = [n["name"] for n in path.nodes]
                    rels = [r.get("type", "相关") for r in path.relationships]
                    paths.append({"nodes": nodes, "relations": rels})
                
                return paths
        except Exception as e:
            print(f"Failed to find path: {e}")
            return []
    
    def get_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        if not self.driver:
            return {"notes": 0, "entities": 0, "relations": 0}
        
        try:
            with self.driver.session() as session:
                note_count = session.run("MATCH (n:Note) RETURN count(n) as c").single()["c"]
                entity_count = session.run("MATCH (e:Entity) RETURN count(e) as c").single()["c"]
                relation_count = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) as c").single()["c"]
                
                return {
                    "notes": note_count,
                    "entities": entity_count,
                    "relations": relation_count
                }
        except Exception as e:
            return {"notes": 0, "entities": 0, "relations": 0, "error": str(e)}
    
    def delete_note(self, note_id: str) -> bool:
        """删除笔记及其关联的实体关系"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # 删除笔记节点及其关系
                session.run("""
                    MATCH (n:Note {id: $note_id})
                    OPTIONAL MATCH (n)-[:CONTAINS]->(e:Entity)
                    OPTIONAL MATCH (e)-[r:RELATES]-()
                    DELETE r, e, n
                """, {"note_id": note_id})
            return True
        except Exception as e:
            print(f"Failed to delete from graph: {e}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.driver = None
