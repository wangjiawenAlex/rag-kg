"""Knowledge graph search service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Triple:
    """Knowledge graph triple."""

    subject: str
    predicate: str
    obj: str
    confidence: float = 0.5


@dataclass
class KGPath:
    """Knowledge graph path result."""

    path_id: str
    triples: List[Triple]
    confidence: float
    provenance: Optional[List[Dict]] = None


class KGService:
    """Knowledge graph service backed by Neo4j."""

    def __init__(self, neo4j_client=None, ner_model=None, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.neo4j_client = neo4j_client
        self.ner_model = ner_model
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        # 预加载实体库（用于规则匹配NER）
        self._entity_cache = {
            "departments": [],
            "employees": [],
            "positions": []
        }
        self._cache_loaded = False

    async def connect(self) -> None:
        """Create Neo4j connection if needed."""
        if self.neo4j_client and hasattr(self.neo4j_client, "execute_query"):
            if hasattr(self.neo4j_client, "connect"):
                await self.neo4j_client.connect()
            return
        if self.driver is not None:
            return

        from neo4j import AsyncGraphDatabase

        if not (self.uri and self.user and self.password):
            raise ValueError("Neo4j connection info is missing")

        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
        await self.driver.verify_connectivity()

    async def close(self) -> None:
        """Close Neo4j driver."""
        if self.neo4j_client and hasattr(self.neo4j_client, "disconnect"):
            await self.neo4j_client.disconnect()
        if self.driver is not None:
            await self.driver.close()
            self.driver = None

    async def _run(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        params = params or {}
        if self.neo4j_client and hasattr(self.neo4j_client, "execute_query"):
            return await self.neo4j_client.execute_query(query, params)

        await self.connect()
        async with self.driver.session() as session:
            result = await session.run(query, params)
            records = []
            async for record in result:
                records.append(record.data())
            return records

    async def upsert_triples(self, triples: List[Triple]) -> int:
        """Upsert triples into Neo4j."""
        count = 0
        for triple in triples:
            rel_type = self._safe_rel_type(triple.predicate)
            query = f"""
            MERGE (s:Entity {{name: $subject}})
            MERGE (o:Entity {{name: $object}})
            MERGE (s)-[r:`{rel_type}`]->(o)
            SET r.confidence = $confidence,
                r.predicate = $predicate,
                r.updated_at = datetime()
            RETURN id(r) AS rel_id
            """
            await self._run(
                query,
                {
                    "subject": triple.subject,
                    "object": triple.obj,
                    "predicate": triple.predicate,
                    "confidence": float(triple.confidence),
                },
            )
            count += 1
        return count

    async def add_triples(self, triples: List[Triple]) -> int:
        """Compatibility wrapper for legacy code path."""
        normalized = [t if isinstance(t, Triple) else Triple(**t) for t in triples]
        return await self.upsert_triples(normalized)

    async def search(self, query: str, top_k: int = 5, max_hops: int = 2) -> List[KGPath]:
        """Search knowledge graph for paths around extracted entities."""
        # 检测是否包含月薪相关查询
        salary_keywords = ['月薪', '工资', '薪资', '收入', ' salary', ' salary']
        has_salary_query = any(kw in query for kw in salary_keywords)
        
        # 如果是月薪查询，使用专门的逻辑
        if has_salary_query:
            return await self._search_salary(query, top_k)
        
        # 检测统计查询（"有多少人"、"多少人"、"几个部门"）
        count_keywords = ['有多少人', '多少人', '几口', '多少员工', '几个部门', '多少部门', '多少个部门', '有哪些部门', '部门有哪些']
        is_count_query = any(kw in query for kw in count_keywords)
        
        if is_count_query:
            return await self._search_count(query, top_k)
        
        # 原有逻辑
        entities = await self.extract_entities(query)
        if not entities:
            return []

        # 对每个实体分别查询再合并（解决IN查询的问题）
        all_paths = []
        for entity in entities[:4]:  # 最多查4个实体
            cypher = """
            MATCH (start:Entity {name: $entity})
            MATCH p=(start)-[r*1..""" + str(max_hops) + """]-(end:Entity)
            RETURN p
            LIMIT """ + str(max(top_k, 8)) + """
            """
            try:
                rows = await self._run(cypher, {"entity": entity})
                for row in rows:
                    path_obj = row.get("p")
                    triples = self._triples_from_path(path_obj)
                    if triples:
                        confidence = sum(t.confidence for t in triples) / len(triples)
                        all_paths.append(KGPath(
                            path_id=f"path-{len(all_paths)}",
                            triples=triples,
                            confidence=confidence
                        ))
            except:
                pass
        
        return all_paths[:top_k]
    
    async def _search_count(self, query: str, top_k: int) -> List[KGPath]:
        """Search count information (e.g., how many people in a department)."""
        # 预加载实体库
        await self._ensure_entity_cache()
        
        # 检测是否是"几个部门"类查询
        dept_count_keywords = ['几个部门', '多少部门', '多少个部门', '有哪些部门', '部门有哪些']
        is_dept_list_query = any(kw in query for kw in dept_count_keywords)
        
        if is_dept_list_query:
            # 查询所有部门
            dept_count = len(self._entity_cache["departments"])
            dept_names = ", ".join(self._entity_cache["departments"])
            triple = Triple(
                subject="公司",
                predicate="部门列表",
                obj=dept_names,
                confidence=1.0
            )
            return [KGPath(
                path_id="dept-list-0",
                triples=[triple],
                confidence=1.0
            )]
        
        # 找部门
        department = None
        for dept in self._entity_cache["departments"]:
            if dept in query:
                department = dept
                break
        
        if not department:
            # 尝试用部门简称匹配
            for dept in self._entity_cache["departments"]:
                dept_short = dept.replace("部", "")
                if dept_short in query:
                    department = dept
                    break
        
        if not department:
            return []
        
        # 查询部门人数
        cypher = """
        MATCH (d:Department {name: $dept})-[r:BELONGS_TO]-(e:Employee)
        RETURN count(e) as count
        """
        try:
            rows = await self._run(cypher, {"dept": department})
            for row in rows:
                count = row.get("count", 0)
                triple = Triple(
                    subject=department,
                    predicate="部门总人数",
                    obj=str(count),
                    confidence=1.0
                )
                return [KGPath(
                    path_id="count-0",
                    triples=[triple],
                    confidence=1.0
                )]
        except:
            pass
        
        return []
        rows = await self._run(cypher, {"entities": entities})

        paths: List[KGPath] = []
        for idx, row in enumerate(rows):
            path_obj = row.get("p")
            triples = self._triples_from_path(path_obj)
            if not triples:
                continue
            confidence = sum(t.confidence for t in triples) / len(triples)
            paths.append(KGPath(path_id=f"path-{idx:03d}", triples=triples, confidence=confidence, provenance=None))
        return paths
    
    async def _search_salary(self, query: str, top_k: int) -> List[KGPath]:
        """Search salary information from knowledge graph."""
        entities = await self.extract_entities(query)
        
        # 确定是查部门还是查员工
        department = None
        employee = None
        
        # 尝试找部门
        for ent in entities:
            if ent in ['技术部', '产品部', '财务部', '人事部', '市场部', '销售部', '运营部']:
                department = ent
                break
        
        # 尝试找员工
        if not department:
            for ent in entities:
                if '员工' in ent:
                    employee = ent
        
        paths = []
        
        # 查询特定部门的工资最高员工
        if department:
            cypher = f"""
            MATCH (d:Department {{name: $dept}})<-[:BELONGS_TO]-(e:Employee)-[:HAS_SALARY]->(s:Salary)
            RETURN e.name as name, s.amount as salary
            ORDER BY s.amount DESC
            LIMIT {top_k}
            """
            rows = await self._run(cypher, {"dept": department})
            
            for idx, row in enumerate(rows):
                name = row.get("name", "未知")
                salary = row.get("salary", 0)
                # 构建三元组
                triples = [
                    Triple(
                        subject=f"{department}",
                        predicate="部门员工",
                        obj=name,
                        confidence=0.9
                    ),
                    Triple(
                        subject=name,
                        predicate="月薪",
                        obj=f"{salary}元",
                        confidence=0.9
                    )
                ]
                paths.append(KGPath(
                    path_id=f"salary-{idx:03d}",
                    triples=triples,
                    confidence=0.9,
                    provenance=None
                ))
        
        # 查询特定员工的工资
        elif employee:
            cypher = """
            MATCH (e:Employee {name: $emp})-[:HAS_SALARY]->(s:Salary)
            RETURN e.name as name, s.amount as salary
            """
            rows = await self._run(cypher, {"emp": employee})
            
            for idx, row in enumerate(rows):
                name = row.get("name", "未知")
                salary = row.get("salary", 0)
                triples = [
                    Triple(
                        subject=name,
                        predicate="月薪",
                        obj=f"{salary}元",
                        confidence=0.9
                    )
                ]
                paths.append(KGPath(
                    path_id=f"salary-{idx:03d}",
                    triples=triples,
                    confidence=0.9,
                    provenance=None
                ))
        
        return paths

    async def _ensure_entity_cache(self) -> None:
        """预加载实体库到内存（只执行一次）"""
        if self._cache_loaded:
            return
        try:
            # 加载部门
            rows = await self._run("MATCH (d:Department) RETURN d.name as name", {})
            self._entity_cache["departments"] = [row["name"] for row in rows]
            # 加载员工
            rows = await self._run("MATCH (e:Entity) RETURN e.name as name", {})
            self._entity_cache["employees"] = [row["name"] for row in rows if row.get("name")]
            # 加载职位
            rows = await self._run("MATCH (e:Entity) RETURN DISTINCT e.position as pos", {})
            self._entity_cache["positions"] = [row["pos"] for row in rows if row.get("pos")]
            self._cache_loaded = True
        except Exception as e:
            pass

    async def extract_entities(self, text: str) -> List[str]:
        """Extract entities from text using rule-based NER."""
        # 使用NER模型（如果可用）
        if hasattr(self.ner_model, "extract"):
            return self.ner_model.extract(text)

        # 预加载实体库
        await self._ensure_entity_cache()
        
        entities = []
        
        # 1. 精确匹配部门
        for dept in self._entity_cache["departments"]:
            if dept in text:
                entities.append(dept)
        
        # 2. 精确匹配员工姓名
        for emp in self._entity_cache["employees"]:
            if emp in text:
                entities.append(emp)
        
        # 3. 规则匹配中文实体
        import re
        # 匹配 "XX部"、"XX部门"
        dept_patterns = [
            r'([\u4e00-\u9fa5]{2,5})(?:部|部门|科室|组)',
        ]
        for pattern in dept_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        # 4. 匹配"有哪些部门"、"部门有哪些"等问题
        if any(kw in text for kw in ["哪些部门", "有什么部门", "部门有哪些"]):
            # 直接返回所有部门
            entities.extend(self._entity_cache["departments"])
        
        # 5. 匹配"负责人"、"主管"等问题
        if any(kw in text for kw in ["负责人", "主管", "老板", "管理"]):
            # 提取可能的部门名称
            for dept in self._entity_cache["departments"]:
                dept_short = dept.replace("部", "").replace("部门", "")
                if dept_short in text:
                    if dept not in entities:
                        entities.append(dept)
        
        # 过滤无意义的实体
        stop_words = ["公司有哪些", "公司有哪", "有哪些", "什么部"]
        entities = [e for e in entities if e not in stop_words and len(e) >= 2]
        
        # 去重并返回
        return list(dict.fromkeys(entities))[:8]

    async def find_path(self, entity_from: str, entity_to: Optional[str] = None, max_hops: int = 2) -> List[KGPath]:
        """Find paths between entities in KG."""
        if entity_to:
            query = """
            MATCH p = shortestPath((a:Entity {name: $from})-[*..""" + str(max_hops) + """]-(b:Entity {name: $to}))
            RETURN p
            LIMIT 5
            """
            rows = await self._run(query, {"from": entity_from, "to": entity_to})
        else:
            query = """
            MATCH p=(a:Entity {name: $from})-[*1..""" + str(max_hops) + """]-(b:Entity)
            RETURN p
            LIMIT 5
            """
            rows = await self._run(query, {"from": entity_from})

        results: List[KGPath] = []
        for idx, row in enumerate(rows):
            triples = self._triples_from_path(row.get("p"))
            if triples:
                results.append(KGPath(path_id=f"path-{idx:03d}", triples=triples, confidence=0.8))
        return results

    async def find_subgraph(self, entities: List[str], max_hops: int = 2) -> Dict:
        """Find subgraph around entities."""
        cypher = """
        MATCH (n:Entity)
        WHERE n.name IN $entities
        OPTIONAL MATCH p=(n)-[*1..""" + str(max_hops) + """]-(m)
        RETURN collect(DISTINCT n.name) AS seeds,
               collect(DISTINCT m.name) AS neighbors
        """
        rows = await self._run(cypher, {"entities": entities})
        if not rows:
            return {"nodes": entities, "edges": []}
        row = rows[0]
        nodes = [n for n in (row.get("seeds", []) + row.get("neighbors", [])) if n]
        return {"nodes": list(dict.fromkeys(nodes)), "edges": []}

    @staticmethod
    def _safe_rel_type(value: str) -> str:
        rel = re.sub(r"[^A-Za-z0-9_]", "_", value.strip())
        rel = re.sub(r"_+", "_", rel)
        rel = rel.strip("_") or "RELATED_TO"
        return rel.upper()

    def _triples_from_path(self, path_obj) -> List[Triple]:
        """Extract triples from a path object.
        
        Handles both neo4j 5.x (Path object) and 6.x (list) APIs.
        neo4j 6.x returns path as [node_dict, rel_type_str, node_dict, ...]
        """
        if path_obj is None:
            return []
        triples: List[Triple] = []
        
        try:
            # neo4j 6.x: path is a list [node, rel_type, node, rel_type, node, ...]
            if isinstance(path_obj, list) and len(path_obj) >= 3:
                # Format: [node_dict, 'REL_TYPE', node_dict, 'REL_TYPE', node_dict, ...]
                for i in range(1, len(path_obj) - 1, 2):
                    if i + 1 < len(path_obj):
                        # path[i-1] is start node, path[i] is rel type, path[i+1] is end node
                        start_node = path_obj[i - 1]
                        predicate = path_obj[i]
                        end_node = path_obj[i + 1]
                        
                        # Extract names from node dicts
                        if isinstance(start_node, dict):
                            subject = start_node.get("name", str(start_node))
                        else:
                            subject = str(start_node)
                            
                        if isinstance(end_node, dict):
                            obj = end_node.get("name", str(end_node))
                        else:
                            obj = str(end_node)
                        
                        # Handle predicate (string or dict)
                        if isinstance(predicate, dict):
                            pred_name = predicate.get("predicate", predicate.get("type", "RELATED_TO"))
                        else:
                            pred_name = str(predicate)
                        
                        confidence = 0.8
                        triples.append(Triple(subject=subject, predicate=pred_name, obj=obj, confidence=confidence))
            elif hasattr(path_obj, 'relationships'):
                # neo4j 5.x: path has relationships attribute
                for rel in path_obj.relationships:
                    subject = rel.start_node.get("name")
                    obj = rel.end_node.get("name")
                    predicate = rel.get("predicate") or rel.type
                    confidence = float(rel.get("confidence", 0.8))
                    triples.append(Triple(subject=subject, predicate=predicate, obj=obj, confidence=confidence))
        except Exception as e:
            print(f"Error extracting triples: {e}")
            return []
        return triples
