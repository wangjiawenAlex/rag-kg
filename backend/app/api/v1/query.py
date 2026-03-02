"""
Query API endpoint.

Handles user queries and returns answers with evidence.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.security import decode_token
from app.core.config import get_settings

router = APIRouter(prefix="/query", tags=["query"])


class Evidence(BaseModel):
    """Evidence item."""
    id: str
    source: str  # "vector" or "kg"
    text: str
    score: float
    metadata: Optional[dict] = None


class RouterDecision(BaseModel):
    """Router decision info."""
    strategy: str  # "VECTOR_ONLY", "KG_ONLY", "KG_THEN_VECTOR", "HYBRID_JOIN"
    reason: str


class QueryRequest(BaseModel):
    """Query request payload."""
    query: str
    session_id: Optional[str] = None
    top_k: int = 5
    use_reader: bool = True
    router_hint: Optional[str] = None


class QueryResponse(BaseModel):
    """Query response payload."""
    answer: str
    evidence: List[Evidence]
    router_decision: RouterDecision
    latency_ms: int
    sources: Optional[List[dict]] = None


def get_current_user(authorization: Optional[str] = Header(None)):
    """Extract user from authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    settings = get_settings()
    payload = decode_token(token, settings.secret_key, settings.algorithm)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload.get("sub")


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    user_id: str = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    """
    Main query endpoint.
    
    Args:
        request: QueryRequest with query text and options
        user_id: Current user ID from auth
        authorization: Bearer token for auth
    
    Returns:
        QueryResponse with answer, evidence, and routing decision
    """
    from fastapi import Request
    from app.main import app
    
    # Get router service from app state
    router_service = app.state.router_service
    
    # Process query
    result = await router_service.handle_query(
        user_id=user_id,
        session_id=request.session_id,
        query=request.query,
        top_k=request.top_k,
        router_hint=request.router_hint
    )
    
    # Convert evidence
    evidence = [
        Evidence(**ev) for ev in result.get("evidence", [])
    ]
    
    return QueryResponse(
        answer=result["answer"],
        evidence=evidence,
        router_decision=RouterDecision(**result["router_decision"]),
        latency_ms=result["latency_ms"],
        sources=result.get("sources")
    )


@router.get("/history/{session_id}")
async def get_query_history(
    session_id: str,
    user_id: str = Depends(get_current_user)
):
    """
    Get query history for a session.
    
    Args:
        session_id: Session identifier
        user_id: Current user ID
    
    Returns:
        List of past queries and responses
    """
    # Mock implementation
    return {
        "session_id": session_id,
        "user_id": user_id,
        "queries": []
    }
