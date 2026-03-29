"""
Reader and answer generation service.

Handles answer generation and reranking of candidates.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Candidate:
    """Retrieval candidate."""
    id: str
    text: str
    score: float
    source: str  # "vector" or "kg"
    metadata: Optional[Dict] = None


@dataclass
class Answer:
    """Generated answer."""
    text: str
    confidence: float
    sources: List[str]


class RerankerService:
    """Candidate reranking service."""
    
    def __init__(self, cross_encoder=None):
        """
        Initialize reranker.
        
        Args:
            cross_encoder: Optional cross-encoder model for reranking
        """
        # TODO: Implement
        # 1. Store cross-encoder reference
        self.cross_encoder = cross_encoder
    
    def merge_and_score(
        self,
        vector_hits: List,
        kg_paths: List,
        query: str
    ) -> List[Candidate]:
        """
        Merge vector and KG results and rerank.
        
        Args:
            vector_hits: Vector search results
            kg_paths: KG search results
            query: Original query
        
        Returns:
            Merged and reranked candidates
        """
        candidates = []
        
        # Convert vector hits to candidates
        for hit in vector_hits:
            candidates.append(Candidate(
                id=hit.id,
                text=hit.text,
                score=hit.score,
                source="vector",
                metadata=hit.metadata
            ))
        
        # Convert KG paths to candidates
        for i, path in enumerate(kg_paths):
            kg_text = " → ".join([f"{t.subject}-{t.predicate}-{t.obj}" for t in path.triples])
            candidates.append(Candidate(
                id=f"kg-path-{i}",
                text=kg_text,
                score=path.confidence,
                source="kg",
                metadata={"path_id": path.path_id}
            ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates


class ReaderService:
    """Answer generation service."""
    
    def __init__(self, llm_client=None, use_template=True):
        """
        Initialize reader.
        
        Args:
            llm_client: Optional LLM client for generation
            use_template: Whether to use template-based generation (default: True for backwards compatibility)
        """
        # TODO: Implement
        # 1. Store LLM client reference
        # 2. Store template preference
        self.llm_client = llm_client
        # If LLM client is provided, use it by default
        self.use_template = not bool(llm_client)
    
    def _is_meaningful_query(self, query: str) -> bool:
        """Check if query is meaningful enough to process."""
        if not query or len(query.strip()) == 0:
            return False
        cleaned = query.strip()
        if len(cleaned) <= 1:
            return False
        # Must contain at least one CJK character or meaningful English word
        has_cjk = any('\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf' for c in cleaned)
        has_en = any(c.isalpha() and ord(c) < 128 for c in cleaned)
        if not (has_cjk or has_en):
            return False
        return True

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract searchable terms from query (n-grams for Chinese)."""
        q = query.strip()
        if not q:
            return []
        
        terms = set()
        
        # Chinese n-gram extraction (2-gram and 3-gram sliding window)
        chinese_segs = []
        i = 0
        while i < len(q):
            c = q[i]
            if '\u4e00' <= c <= '\u9fff' or '\u3400' <= c <= '\u4dbf':
                j = i
                while j < len(q) and ('\u4e00' <= q[j] <= '\u9fff' or '\u3400' <= q[j] <= '\u4dbf'):
                    j += 1
                chinese_segs.append(q[i:j])
                i = j
            else:
                i += 1
        
        if chinese_segs:
            # Build a combined Chinese string
            combined = ''.join(chinese_segs)
            # Add n-grams (2 to 4 chars)
            for n in range(2, min(5, len(combined) + 1)):
                for i in range(len(combined) - n + 1):
                    terms.add(combined[i:i+n])
            # Also add full segments >= 2
            for seg in chinese_segs:
                if len(seg) >= 2:
                    terms.add(seg)
        
        # English words 3+
        import re
        for w in re.findall(r'[a-zA-Z]{3,}', q):
            terms.add(w.lower())
        
        return list(terms)

    def _check_context_relevance(self, query: str, candidates: List[Candidate]) -> Dict:
        """
        Check if retrieved context is actually relevant to the query.
        
        Returns:
            Dict with is_relevant and reason
        """
        if not candidates or not query:
            return {"is_relevant": False, "reason": "No candidates or query"}
        
        terms = self._extract_search_terms(query)
        
        if not terms:
            return {"is_relevant": False, "reason": "No meaningful query terms"}
        
        # Check how many candidates actually mention query terms
        relevant_count = 0
        for c in candidates:
            text = c.text
            # Check if any term appears
            has_match = any(term in text for term in terms)
            if has_match:
                relevant_count += 1
        
        total = len(candidates)
        relevance_ratio = relevant_count / total if total > 0 else 0
        
        if relevance_ratio == 0:
            return {
                "is_relevant": False,
                "reason": f"检索结果与查询无关（0/{total}条包含查询关键词）"
            }
        elif relevance_ratio < 0.3:
            return {
                "is_relevant": False,
                "reason": f"检索结果大部分不相关（{relevant_count}/{total}条包含查询关键词）"
            }
        else:
            return {
                "is_relevant": True,
                "reason": f"{relevant_count}/{total}条检索结果与查询相关"
            }

    async def generate_answer(
        self,
        query: str,
        candidates: List[Candidate],
        mode: str = "concise"
    ) -> Answer:
        """
        Generate answer from candidates with intelligent routing.
        
        Args:
            query: Query text
            candidates: Ranked candidates
            mode: Generation mode ("concise" or "detailed")
        
        Returns:
            Generated answer
        """
        # Filter out meaningless queries first
        if not self._is_meaningful_query(query):
            return Answer(
                text="抱歉，您的提问太简短了，无法理解您的意思。请换个更具体的问题，比如\"五险一金怎么缴纳？\"或\"年终奖什么时候发？\"",
                confidence=0.0,
                sources=[]
            )
        
        # Check retrieval quality
        quality = self._assess_retrieval_quality(candidates, query)
        
        # Critical: check context relevance
        context_relevance = self._check_context_relevance(query, candidates)
        
        # If context is not relevant to query, refuse to answer
        if not context_relevance["is_relevant"]:
            return Answer(
                text=f"抱歉，目前没有找到与\"{query}\"相关的信息。\n\n请换个问题试试，或者使用更完整的描述，例如\"五险一金\"、\"年终奖\"、\"请假制度\"等。",
                confidence=0.0,
                sources=[]
            )
        
        if self.llm_client:
            return await self._llm_answer(query, candidates, mode, quality)
        elif self.use_template:
            return await self._template_answer(candidates, mode)
        else:
            return await self._llm_answer(query, candidates, mode, quality)
    
    def _assess_retrieval_quality(self, candidates: List[Candidate], query: str = "") -> Dict:
        """
        Assess the quality of retrieval results.
        
        Args:
            candidates: List of retrieved candidates
            query: Original query text (for content relevance check)
        
        Returns:
            Dictionary with quality metrics
        """
        if not candidates:
            return {
                "is_adequate": False,
                "has_evidence": False,
                "top_score": 0.0,
                "total_candidates": 0,
                "reason": "No retrieval results found"
            }
        
        top_score = candidates[0].score if candidates else 0.0
        total_candidates = len(candidates)
        
        # Thresholds for adequacy
        HIGH_SCORE_THRESHOLD = 0.40
        LOW_SCORE_THRESHOLD = 0.30
        MIN_CANDIDATES = 3
        
        # Check content relevance (basic keyword matching)
        is_content_relevant = True
        if query and candidates:
            # Extract key terms from query (longer than 2 chars)
            query_terms = set(term for term in query if len(term) > 2)
            # Check if any candidate text contains query terms
            relevant_count = 0
            for c in candidates:
                # Simple relevance: candidate text contains some query terms
                candidate_text_lower = c.text.lower()
                query_lower = query.lower()
                # Check if key words from query appear in candidate
                has_match = any(term.lower() in candidate_text_lower for term in query_terms)
                if has_match:
                    relevant_count += 1
            # If less than half candidates are relevant, mark as not adequate
            if relevant_count == 0:
                is_content_relevant = False
            elif relevant_count < total_candidates / 2:
                is_content_relevant = False
        
        # Determine adequacy
        has_high_score = top_score >= HIGH_SCORE_THRESHOLD
        has_enough_candidates = total_candidates >= MIN_CANDIDATES
        
        is_adequate = has_high_score or (top_score >= LOW_SCORE_THRESHOLD and has_enough_candidates and is_content_relevant)
        
        reason = ""
        if not candidates:
            reason = "No retrieval results"
        elif not is_content_relevant:
            reason = f"Content not relevant to query (score: {top_score:.3f})"
        elif not is_adequate:
            reason = f"Top score {top_score:.3f} below threshold"
        else:
            reason = f"Adequate retrieval with top score {top_score:.3f}"
        
        return {
            "is_adequate": is_adequate,
            "has_evidence": total_candidates > 0,
            "top_score": top_score,
            "total_candidates": total_candidates,
            "is_content_relevant": is_content_relevant,
            "reason": reason
        }
    
    async def _template_answer(
        self,
        candidates: List[Candidate],
        mode: str
    ) -> Answer:
        """
        Generate answer using templates.
        
        Args:
            candidates: Ranked candidates
            mode: Generation mode
        
        Returns:
            Generated answer
        """
        if not candidates:
            return Answer(text="No answer found.", confidence=0.0, sources=[])
        
        top_candidate = candidates[0]
        answer_text = f"Based on {top_candidate.source} search: {top_candidate.text[:200]}..."
        
        return Answer(
            text=answer_text,
            confidence=top_candidate.score,
            sources=[c.id for c in candidates[:3]]
        )
    
    async def _llm_answer(
        self,
        query: str,
        candidates: List[Candidate],
        mode: str,
        quality: Dict
    ) -> Answer:
        """
        Generate answer using LLM with intelligent routing.
        
        Args:
            query: Query text
            candidates: Ranked candidates
            mode: Generation mode
            quality: Retrieval quality assessment
        
        Returns:
            Generated answer
        """
        if not self.llm_client:
            # Fallback to template if no LLM client
            return await self._template_answer(candidates, mode)
        
        # Build context from candidates
        context_parts = []
        for i, c in enumerate(candidates[:5]):  # Use top 5 candidates
            context_parts.append(f"[{i+1}] ({c.source}) {c.text[:300]}")
        context = "\n\n".join(context_parts)
        
        # Build prompt based on retrieval quality
        if quality["is_adequate"]:
            # Good retrieval - answer based on evidence
            if mode == "detailed":
                system_prompt = """你是一个专业的企业知识问答助手。你的回答必须严格按照以下规则：

1. **优先使用检索到的证据**：如果知识库中有相关信息，必须基于证据回答
2. **回答要人性化**：使用友好的语气，像专业人士一样解答问题
3. **清晰有条理**：使用列表、强调重点，让回答易于理解
4. **只回答有依据的内容**：如果证据不足，明确说明"根据现有资料"

请基于以下检索到的信息回答用户问题："""
            else:
                system_prompt = """你是一个专业、友好的企业知识问答助手。请严格按照以下规则回答：

1. 先看知识库有没有相关信息
2. 如果有，用自己的话总结回答（不要复制粘贴）
3. 回答要亲切、自然，像人与人交流
4. 找不到答案时，直接说"抱歉，目前没有找到相关信息"

请根据以下资料回答："""
        else:
            # Poor retrieval - allow LLM to use general knowledge with fallback
            if mode == "detailed":
                system_prompt = """你是一个专业、友好的企业知识问答助手。请按照以下规则回答：

**首先**：尝试用以下检索到的资料回答（如果有相关的话）
**然后**：如果资料不足或不相关，请基于你的常识来回答，并说明：
- "根据一般经验..."
- "通常来说..."
- "在没有具体公司规定的情况下，我建议..."

注意：即使是基于常识回答，也要尽量给出一个有用、友好的答案。"""
            else:
                system_prompt = """你是一个热情友好的企业顾问。用户问了一个问题，但知识库里可能没有完整答案。

**请这样处理：**
1. 先看看下面有没有相关资料，有就用来回答
2. 如果资料很少或者不相关，请用你的常识来补充回答
3. 回答要像朋友聊天一样自然，不要机械
4. 可以加一句："目前资料库中没有完整信息，但从一般经验来看..."

记住：给出一个友好的回答比说"找不到"更有价值！

相关资料："""
        
        try:
            # Call LLM (sync version for simplicity)
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, run in executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        self.llm_client.generate_sync,
                        query,
                        context,
                        system_prompt
                    )
                    response = future.result(timeout=30)
            else:
                response = self.llm_client.generate_sync(query, context, system_prompt)
            
            # Include quality info in response
            confidence = 0.85 if quality["is_adequate"] else 0.5
            
            return Answer(
                text=response.text,
                confidence=confidence,
                sources=[c.id for c in candidates[:3]]
            )
        except Exception as e:
            # Fallback to template on error
            return await self._template_answer(candidates, mode)
