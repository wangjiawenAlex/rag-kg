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
        entities = await self.extract_entities(query)
        if not entities:
            return []

        cypher = """
        MATCH (start:Entity)
        WHERE any(name in $entities WHERE toLower(start.name) CONTAINS toLower(name))
        MATCH p=(start)-[r*1..""" + str(max_hops) + """]-(end:Entity)
        RETURN p
        LIMIT """ + str(top_k) + """
        """
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

    async def extract_entities(self, text: str) -> List[str]:
        """Extract entities from text."""
        if hasattr(self.ner_model, "extract"):
            return self.ner_model.extract(text)

        terms = [w.strip(".,!?()[]{}") for w in text.split()]
        entities = [t for t in terms if len(t) > 3]
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
