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
    
    async def generate_answer(
        self,
        query: str,
        candidates: List[Candidate],
        mode: str = "concise"
    ) -> Answer:
        """
        Generate answer from candidates.
        
        Args:
            query: Query text
            candidates: Ranked candidates
            mode: Generation mode ("concise" or "detailed")
        
        Returns:
            Generated answer
        """
        if self.llm_client:
            return await self._llm_answer(query, candidates, mode)
        elif self.use_template:
            return await self._template_answer(candidates, mode)
        else:
            return await self._llm_answer(query, candidates, mode)
    
    async def generate_answer(
        self,
        query: str,
        candidates: List[Candidate],
        mode: str = "concise"
    ) -> Answer:
        """
        Generate answer from candidates.
        
        Args:
            query: Query text
            candidates: Ranked candidates
            mode: Generation mode ("concise" or "detailed")
        
        Returns:
            Generated answer
        """
        if self.use_template:
            return await self._template_answer(candidates, mode)
        else:
            return await self._llm_answer(query, candidates, mode)
    
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
        mode: str
    ) -> Answer:
        """
        Generate answer using LLM.
        
        Args:
            query: Query text
            candidates: Ranked candidates
            mode: Generation mode
        
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
        
        # Build prompt based on mode
        if mode == "detailed":
            system_prompt = "You are a helpful AI assistant. Provide detailed answers based on the given context. Cite your sources."
        else:
            system_prompt = "You are a helpful AI assistant. Provide concise answers based on the given context."
        
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
            
            return Answer(
                text=response.text,
                confidence=0.85,
                sources=[c.id for c in candidates[:3]]
            )
        except Exception as e:
            # Fallback to template on error
            return await self._template_answer(candidates, mode)
