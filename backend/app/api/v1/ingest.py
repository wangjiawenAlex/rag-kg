"""
Data ingestion API endpoints.

Handles document and triple ingestion.
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
from app.api.v1.query import get_current_user
from app.services.ingest_service import Document

router = APIRouter(prefix="/ingest", tags=["ingest"])


class DocumentMetadata(BaseModel):
    """Document metadata."""
    doc_id: str
    title: str
    source: str
    published_at: Optional[str] = None
    metadata: Optional[dict] = None


class IngestDocumentsRequest(BaseModel):
    """Ingest documents request."""
    documents: List[DocumentMetadata]
    chunk_size: int = 512
    chunk_overlap: int = 50


class IngestDocumentsResponse(BaseModel):
    """Ingest documents response."""
    total_documents: int
    total_chunks: int
    successful: int
    failed: int
    errors: Optional[List[dict]] = None


class TripleData(BaseModel):
    """Knowledge graph triple."""
    id: str
    subject: str
    predicate: str
    obj: str
    confidence: float
    provenance: Optional[dict] = None


class IngestTriplesRequest(BaseModel):
    """Ingest triples request."""
    triples: List[TripleData]


@router.post("/documents", response_model=IngestDocumentsResponse)
async def ingest_documents(
    request: IngestDocumentsRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Ingest documents and chunk them for vector search.
    
    Args:
        request: IngestDocumentsRequest with documents and chunking params
        user_id: Current user ID
    
    Returns:
        IngestDocumentsResponse with statistics
    """
    from app.main import app
    
    ingest_service = app.state.ingest_service
    
    # Convert to Document objects
    documents = [
        Document(
            doc_id=d.doc_id,
            title=d.title,
            text=f"Document {d.doc_id}: Sample content",  # Mock text
            source=d.source,
            metadata=d.metadata
        )
        for d in request.documents
    ]
    
    # Validate documents
    valid_docs, errors = await ingest_service.validate_documents(documents)
    
    if not valid_docs:
        raise HTTPException(status_code=400, detail="No valid documents to ingest")
    
    # Ingest documents
    result = await ingest_service.ingest_documents(
        valid_docs,
        request.chunk_size,
        request.chunk_overlap
    )
    
    return IngestDocumentsResponse(**result)


@router.post("/documents/file")
async def ingest_documents_from_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload and ingest documents from file (JSONL format).
    
    Args:
        file: JSONL file with documents
        user_id: Current user ID
    
    Returns:
        IngestDocumentsResponse
    """
    content = await file.read()
    lines = content.decode().strip().split('\n')
    
    documents_data = []
    for line in lines:
        if line.strip():
            documents_data.append(json.loads(line))
    
    request = IngestDocumentsRequest(documents=documents_data)
    return await ingest_documents(request, user_id)


@router.post("/triples")
async def ingest_triples(
    request: IngestTriplesRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Ingest knowledge graph triples.
    
    Args:
        request: IngestTriplesRequest with triples
        user_id: Current user ID
    
    Returns:
        Response with success/failure stats
    """
    from app.main import app
    
    ingest_service = app.state.ingest_service
    
    # Convert to dict format
    triples_list = [
        {
            "subject": t.subject,
            "predicate": t.predicate,
            "object": t.obj,
            "confidence": t.confidence,
            "provenance": t.provenance
        }
        for t in request.triples
    ]
    
    result = await ingest_service.ingest_triples(triples_list)
    return result


@router.post("/triples/file")
async def ingest_triples_from_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload and ingest triples from file (JSONL format).
    
    Args:
        file: JSONL file with triples
        user_id: Current user ID
    
    Returns:
        Response
    """
    content = await file.read()
    lines = content.decode().strip().split('\n')
    
    triples = []
    for line in lines:
        if line.strip():
            triples.append(json.loads(line))
    
    request = IngestTriplesRequest(triples=triples)
    return await ingest_triples(request, user_id)
