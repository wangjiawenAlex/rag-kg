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
    is_comparative: bool  # 是否比较类问题
    is_procedural: bool   # 是否流程类问题
    has_specific_person: bool  # 是否包含具体人名
    starts_with_how: bool  # 是否以"如何"开头
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
            strategy, reason = self.decide_strategy(features, query)
        
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
        # 1. 检测是否包含具体人名（常见姓氏）
        name_patterns = ['张', '王', '李', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '高', '林', '罗']
        has_specific_person = any(name in query for name in name_patterns) and any(
            suffix in query for suffix in ['在', '是', '的', '工作', '职位', '部门', '向', '会']
        )
        
        # 2. 检测是否为比较类问题
        comparative_words = [
            # 明确比较词
            '区别', '不同', '哪个更好', '哪个更', '有什么不同', '有何不同', '差异', '对比', '比较',
            # 选择建议类
            '应该选', '选哪个', '哪个更适合', '应该选哪个', '选哪一个',
            # 权衡比较类
            '还是', '或者', '哪个更', '哪一个更好', '哪个更合适',
            # 建议类
            '如何选择', '怎么选择', '如何决定', '应该怎么选', '如何取舍',
            # 反义词对比
            '和', '与', '还是', ' versus ', 'vs'
        ]
        is_comparative = any(word in query for word in comparative_words)
        
        # 3. 检测是否为流程类问题（如何、怎么、怎么办）
        procedural_words = ['如何', '怎么', '怎么办', '如何进行', '如何申请', '如何办理', '如何修改', '如何获取']
        is_procedural = any(word in query for word in procedural_words)
        
        # 4. 检测实体特征（部门、技能、职位等）- 但排除流程类问题
        # 如果是流程类问题，优先级更高
        entity_words = ['部', '员工', '经理', '公司', '部门', '组', '职位', '技能', '工资', '汇报']
        has_entity = any(kw in query for kw in entity_words) or has_specific_person
        
        # 5. 检测"如何..."开头的问题（最高优先级）
        starts_with_how = query.startswith('如何') or query.startswith('怎么')
        
        query_length = len(query.split())
        
        # 6. 中英文疑问词检测
        question_words = ['what', 'how', 'why', 'when', 'where', 'which', 'who', 'whom']
        chinese_question_words = ['什么', '怎么', '如何', '为什么', '谁', '哪个', '哪些', '多少', '幾']
        contains_question_word = any(qw in query.lower() for qw in question_words) or any(
            qw in query for qw in chinese_question_words
        )
        
        return QueryFeatures(
            has_entity=has_entity,
            query_length=query_length,
            contains_question_word=contains_question_word,
            is_comparative=is_comparative,
            is_procedural=is_procedural,
            has_specific_person=has_specific_person,
            starts_with_how=starts_with_how,
            embedding=None
        )
    
    def decide_strategy(self, features: QueryFeatures, query: str = "") -> Tuple[RoutingStrategy, str]:
        """
        Decide routing strategy based on features.
        
        Args:
            features: QueryFeatures extracted from query
            query: Original query text (optional, for additional checks)
        
        Returns:
            Tuple of (strategy, reason)
        """
        # 优化后的路由规则（优先级从高到低）：
        
        # 0. 如果query为空，使用features.is_comparative
        if not query:
            query = ""
        
        # 1. HYBRID - 比较类问题（最高优先级）
        # 直接检查query中的关键词，因为features.is_comparative可能不完整
        comparative_keywords = [
            '区别', '不同', '哪个更好', '哪个更', '有什么不同', '有何不同', 
            '差异', '对比', '比较', '应该选', '选哪个', '哪个更适合',
            '还是', '如何选择', '怎么选择', '如何决定', '如何取舍',
            '哪一个更好', '哪一个更合适', '应该先学', '应该如何选择',
            '应该怎么', '选择哪个', '选哪一个'
        ]
        
        # 同时检查"和"或"与"连接的两个事物（需要两边都有内容）
        has_and_compare = ('和' in query and len(query.split('和')) >= 2) or \
                         ('与' in query and len(query.split('与')) >= 2) or \
                         ('还是' in query)
        
        has_comparative = any(kw in query for kw in comparative_keywords) or has_and_compare
        
        if has_comparative:
            return RoutingStrategy.HYBRID_JOIN, f"Query is comparative (contains: 比较关键词 or '和/与'对比) - use both vector and KG"
        
        # 2. VECTOR_ONLY - 以"如何"开头的问题
        if features.starts_with_how:
            return RoutingStrategy.VECTOR_ONLY, "Query starts with '如何' - use vector search only"
        
        # 3. KG_ONLY - 具体人名查询
        if features.has_specific_person:
            return RoutingStrategy.KG_ONLY, "Query contains specific person name (e.g., '张三在...') - use KG only"
        
        # 4. VECTOR_ONLY - 流程类问题，不涉及具体人员
        if features.is_procedural and not features.has_specific_person:
            return RoutingStrategy.VECTOR_ONLY, "Query is procedural (contains '如何'/'怎么办') - use vector search only"
        
        # 5. KG_ONLY - 包含实体但不是比较类和流程类
        if features.has_entity and not features.is_comparative and not features.is_procedural:
            return RoutingStrategy.KG_ONLY, "Query contains domain entities - use KG"
        
        # 6. VECTOR_ONLY - 长描述性问题
        if features.query_length > 15:
            return RoutingStrategy.VECTOR_ONLY, "Long descriptive query - use vector search"
        
        # 7. 默认使用向量检索
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
