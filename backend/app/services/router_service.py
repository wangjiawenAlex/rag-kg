"""
Dynamic routing service.

Core service for routing queries to appropriate retrieval strategies.
"""

from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio


class RoutingStrategy(str, Enum):
    """Available routing strategies."""
    VECTOR_ONLY = "VECTOR_ONLY"
    KG_ONLY = "KG_ONLY"
    KG_THEN_VECTOR = "KG_THEN_VECTOR"
    HYBRID_JOIN = "HYBRID_JOIN"


@dataclass
class QueryFeatures:
    """Extracted query features for routing decision."""
    has_entity: bool
    query_length: int
    contains_question_word: bool
    embedding: Optional[List[float]] = None
    historical_strategy: Optional[str] = None


@dataclass
class RoutingDecision:
    """Routing decision result."""
    strategy: RoutingStrategy
    reason: str
    confidence: float = 0.5


class RouterService:
    """Main routing service."""
    
    def __init__(self, vector_service, kg_service, reranker, reader):
        """
        Initialize router service.
        
        Args:
            vector_service: Vector retrieval service
            kg_service: Knowledge graph service
            reranker: Reranking service
            reader: Reader/answer generation service
        """
        # TODO: Implement
        # 1. Store service references
        # 2. Initialize strategy templates/rules
        self.vector_service = vector_service
        self.kg_service = kg_service
        self.reranker = reranker
        self.reader = reader
    
    async def handle_query(
        self,
        user_id: str,
        session_id: Optional[str],
        query: str,
        top_k: int = 5,
        router_hint: Optional[str] = None
    ) -> Dict:
        """
        Main query handling function.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Query text
            top_k: Number of top results
            router_hint: Optional hint for routing strategy
        
        Returns:
            Dictionary with answer, evidence, and routing decision
        """
        import time
        start_time = time.time()
        
        # Extract features from query
        features = await self._extract_features(query)
        
        # Decide strategy
        if router_hint:
            strategy = RoutingStrategy(router_hint)
            reason = f"User-provided hint: {router_hint}"
        else:
            strategy, reason = self.decide_strategy(features)
        
        # Execute strategy
        vector_hits, kg_paths = await self._execute_strategy(strategy, query, top_k)
        
        # Merge and rerank candidates
        candidates = self.reranker.merge_and_score(vector_hits, kg_paths, query)
        
        # Generate answer
        answer = await self.reader.generate_answer(query, candidates)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Prepare evidence
        evidence = [
            {
                "id": c.id,
                "source": c.source,
                "text": c.text,
                "score": c.score,
                "metadata": c.metadata
            }
            for c in candidates[:top_k]
        ]
        
        return {
            "answer": answer.text if hasattr(answer, 'text') else str(answer),
            "evidence": evidence,
            "router_decision": {
                "strategy": strategy.value,
                "reason": reason,
                "confidence": 0.85
            },
            "latency_ms": latency_ms,
            "sources": [{"id": c.id, "content": c.text[:200]} for c in candidates[:3]]
        }
    
    async def _extract_features(self, query: str) -> QueryFeatures:
        """
        Extract features from query for routing decision.
        
        Args:
            query: Query text
        
        Returns:
            QueryFeatures object
        """
        # Simple feature extraction
        # 检测英文大写词或中文实体特征
        has_entity = any(word.isupper() for word in query.split()) or any(
            kw in query for kw in ['部', '员工', '经理', '公司', '部门', '组']
        )
        query_length = len(query.split())
        
        # 中英文疑问词检测
        question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'whom']
        chinese_question_words = ['什么', '怎么', '如何', '为什么', '谁', '哪个', '哪些', '多少', '幾']
        contains_question_word = any(qw in query.lower() for qw in question_words) or any(
            qw in query for qw in chinese_question_words
        )
        
        return QueryFeatures(
            has_entity=has_entity,
            query_length=query_length,
            contains_question_word=contains_question_word,
            embedding=None
        )
    
    def decide_strategy(self, features: QueryFeatures) -> Tuple[RoutingStrategy, str]:
        """
        Decide routing strategy based on features.
        
        Args:
            features: QueryFeatures extracted from query
        
        Returns:
            Tuple of (strategy, reason)
        """
        # Simple rule-based strategy selection
        if features.has_entity and features.contains_question_word:
            return RoutingStrategy.HYBRID_JOIN, "Query contains entities and question words - use both vector and KG"
        elif features.has_entity:
            return RoutingStrategy.KG_THEN_VECTOR, "Query contains named entities - prefer KG with vector expansion"
        elif features.query_length > 15:
            return RoutingStrategy.VECTOR_ONLY, "Long descriptive query - use vector search"
        elif features.contains_question_word:
            return RoutingStrategy.HYBRID_JOIN, "Question type query - combine both strategies"
        else:
            return RoutingStrategy.VECTOR_ONLY, "Default to vector search"
    
    async def _execute_strategy(
        self,
        strategy: RoutingStrategy,
        query: str,
        top_k: int
    ) -> Tuple[List, List]:
        """
        Execute retrieval strategy.
        
        Args:
            strategy: Routing strategy to execute
            query: Query text
            top_k: Number of results
        
        Returns:
            Tuple of (vector_hits, kg_paths)
        """
        if strategy == RoutingStrategy.VECTOR_ONLY:
            vector_hits = await self.vector_service.search(query, top_k)
            kg_paths = []
        elif strategy == RoutingStrategy.KG_ONLY:
            kg_paths = await self.kg_service.search(query, top_k)
            vector_hits = []
        elif strategy == RoutingStrategy.KG_THEN_VECTOR:
            kg_paths = await self.kg_service.search(query, top_k)
            expanded_q = self._expand_query_from_kg(kg_paths)
            vector_hits = await self.vector_service.search(expanded_q, top_k)
        else:  # HYBRID_JOIN
            vector_hits, kg_paths = await asyncio.gather(
                self.vector_service.search(query, top_k),
                self.kg_service.search(query, top_k)
            )
        
        return vector_hits, kg_paths
    
    def _expand_query_from_kg(self, kg_paths: List) -> str:
        """
        Expand query using entities from KG results.
        
        Args:
            kg_paths: KG search results
        
        Returns:
            Expanded query text
        """
        if not kg_paths:
            return ""
        # Simple expansion: concatenate entity names from paths
        entities = []
        for path in kg_paths:
            if hasattr(path, 'triples'):
                for triple in path.triples:
                    entities.extend([triple.subject, triple.obj])
        return " ".join(set(entities)) if entities else ""
