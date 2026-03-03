"""
Data ingestion service.

Handles document chunking, embedding generation, and data loading.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.services.kg_service import Triple


@dataclass
class Document:
    """Input document."""
    doc_id: str
    title: str
    text: str
    source: str
    metadata: Optional[Dict] = None


@dataclass
class Chunk:
    """Document chunk."""
    chunk_id: str
    doc_id: str
    text: str
    chunk_index: int
    metadata: Optional[Dict] = None


class IngestService:
    """Data ingestion service."""
    
    def __init__(self, vector_service, kg_service, db_client):
        """
        Initialize ingest service.
        
        Args:
            vector_service: Vector service for upserting embeddings
            kg_service: KG service for adding entities
            db_client: Database client for metadata
        """
        # TODO: Implement
        # 1. Store service references
        self.vector_service = vector_service
        self.kg_service = kg_service
        self.db_client = db_client
    
    async def ingest_documents(
        self,
        documents: List[Document],
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Dict:
        """
        Ingest documents.
        
        Args:
            documents: List of documents to ingest
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        
        Returns:
            Ingest statistics
        """
        total_chunks = 0
        successful = 0
        errors = []
        
        for doc in documents:
            try:
                # Chunk the document
                chunks = self._chunk_text(doc.text, chunk_size, chunk_overlap)
                
                # Create chunk objects
                chunk_data = []
                for i, chunk_text in enumerate(chunks):
                    chunk = Chunk(
                        chunk_id=f"{doc.doc_id}::chunk-{i}",
                        doc_id=doc.doc_id,
                        text=chunk_text,
                        chunk_index=i,
                        metadata={
                            **(doc.metadata or {}),
                            "source": doc.source,
                            "title": doc.title
                        }
                    )
                    chunk_data.append(chunk)
                
                # Upsert to vector DB
                if chunk_data:
                    await self.vector_service.upsert([{
                        "id": c.chunk_id,
                        "text": c.text,
                        "metadata": c.metadata
                    } for c in chunk_data])
                
                total_chunks += len(chunks)
                successful += 1
                
            except Exception as e:
                errors.append({"doc_id": doc.doc_id, "error": str(e)})
        
        return {
            "total_documents": len(documents),
            "total_chunks": total_chunks,
            "successful": successful,
            "failed": len(documents) - successful,
            "errors": errors if errors else None
        }
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> List[str]:
        """
        Chunk text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
        
        Returns:
            List of text chunks
        """
        chunks = []
        sentences = text.split('.')
        current_chunk = []
        current_length = 0
        step = chunk_size - chunk_overlap
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length <= chunk_size:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                if current_chunk:
                    chunks.append('. '.join(current_chunk) + '.')
                current_chunk = [sentence]
                current_length = sentence_length
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks
    
    async def ingest_triples(
        self,
        triples: List[Dict]
    ) -> Dict:
        """
        Ingest knowledge graph triples.
        
        Args:
            triples: List of triples with subject, predicate, object
        
        Returns:
            Ingest statistics
        """
        successful = 0
        errors = []
        
        for triple_data in triples:
            try:
                triple = Triple(
                    subject=triple_data.get("subject"),
                    predicate=triple_data.get("predicate"),
                    obj=triple_data.get("object"),
                    confidence=triple_data.get("confidence", 0.8)
                )
                await self.kg_service.add_triples([triple])
                successful += 1
            except Exception as e:
                errors.append({"triple": triple_data, "error": str(e)})
        
        return {
            "total_triples": len(triples),
            "successful": successful,
            "failed": len(triples) - successful,
            "errors": errors if errors else None
        }
    
    async def validate_documents(
        self,
        documents: List[Document]
    ) -> Tuple[List[Document], List[Dict]]:
        """
        Validate documents before ingestion.
        
        Args:
            documents: Documents to validate
        
        Returns:
            Tuple of (valid_documents, errors)
        """
        valid_docs = []
        errors = []
        
        for doc in documents:
            doc_errors = []
            
            if not doc.doc_id:
                doc_errors.append("Missing doc_id")
            if not doc.text or len(doc.text.strip()) == 0:
                doc_errors.append("Empty text")
            if not doc.title:
                doc_errors.append("Missing title")
            
            if doc_errors:
                errors.append({"doc_id": doc.doc_id or "unknown", "errors": doc_errors})
            else:
                valid_docs.append(doc)
        
        return valid_docs, errors
