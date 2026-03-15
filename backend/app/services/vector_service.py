"""Vector database search service."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse


@dataclass
class VectorHit:
    """Single vector search result."""

    id: str
    text: str
    score: float
    metadata: Dict


class VectorService:
    """Vector search service backed by ChromaDB (default) or custom adapters."""

    def __init__(self, db_client=None, embedding_model=None, collection_name: str = "rag_chunks", embedding_dim: int = 384):
        """Initialize vector service."""
        self.db_client = db_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        self._collection = None
        self._chroma_path = "./chroma_data"
        self._chroma_collection = "rag_chunks"

        if isinstance(db_client, dict):
            self.collection_name = db_client.get("collection_name", self.collection_name)
            self.embedding_dim = int(db_client.get("embedding_dim", self.embedding_dim))
            url = db_client.get("url")
            if url:
                if "://" in url:
                    parsed = urlparse(url)
                    self._chroma_path = parsed.path or self._chroma_path
                else:
                    self._chroma_path = url
            self._chroma_path = db_client.get("path", self._chroma_path)
            self._chroma_collection = db_client.get("collection_name", self._chroma_collection)

    async def _ensure_ready(self) -> None:
        """Ensure ChromaDB connection and collection are ready."""
        if self._collection is not None:
            return

        if self.db_client and hasattr(self.db_client, "search") and hasattr(self.db_client, "upsert"):
            # External adapter already provided.
            return

        import chromadb
        from chromadb.config import Settings as ChromaSettings

        def _connect_and_prepare():
            client = chromadb.PersistentClient(
                path=self._chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            return client.get_or_create_collection(name=self._chroma_collection)

        self._collection = await asyncio.to_thread(_connect_and_prepare)

    async def search(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[VectorHit]:
        """Search vector database by query text."""
        embedding = (await self.encode([query]))[0]
        return await self.search_by_embedding(embedding, top_k=top_k, filters=filters)

    async def search_by_embedding(self, embedding: List[float], top_k: int = 5, filters: Optional[Dict] = None) -> List[VectorHit]:
        """Search by embedding vector directly."""
        if self.db_client and hasattr(self.db_client, "search") and hasattr(self.db_client, "upsert"):
            rows = await self.db_client.search(embedding, top_k, filters)
            return [
                VectorHit(
                    id=str(item.get("id", "")),
                    text=item.get("text", ""),
                    score=float(item.get("score", 0.0)),
                    metadata=item.get("metadata", {}) or {},
                )
                for item in rows
            ]

        await self._ensure_ready()


        def _search():
            where = {"doc_id": filters["doc_id"]} if filters and "doc_id" in filters else None
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where,
                include=["metadatas", "documents", "distances"],
            )
            return result

        result = await asyncio.to_thread(_search)

        hits: List[VectorHit] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        for idx, item_id in enumerate(ids):
            distance = float(dists[idx]) if idx < len(dists) else 0.0
            score = max(0.0, 1.0 - distance)
            hits.append(
                VectorHit(
                    id=str(item_id),
                    text=docs[idx] if idx < len(docs) else "",
                    score=score,
                    metadata=metas[idx] if idx < len(metas) and metas[idx] else {},
                )
            )
        return hits

    async def upsert(self, documents: List[Dict]) -> int:
        """Upsert documents to vector database."""
        if not documents:
            return 0

        ids = [str(d["id"]) for d in documents]
        texts = [d.get("text", "") for d in documents]
        metadata = [d.get("metadata", {}) or {} for d in documents]
        vectors = await self.encode(texts)

        if self.db_client and hasattr(self.db_client, "upsert"):
            return await self.db_client.upsert(ids=ids, vectors=vectors, metadata=metadata)

        await self._ensure_ready()

        def _upsert():
            self._collection.upsert(
                ids=ids,
                documents=texts,
                metadatas=metadata,
                embeddings=vectors,
            )

        await asyncio.to_thread(_upsert)
        return len(documents)

    async def delete(self, ids: List[str]) -> int:
        """Delete documents from vector database."""
        if not ids:
            return 0

        if self.db_client and hasattr(self.db_client, "delete"):
            return await self.db_client.delete(ids)

        await self._ensure_ready()

        def _delete():
            self._collection.delete(ids=ids)

        await asyncio.to_thread(_delete)
        return len(ids)

    async def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode texts to embeddings."""
        if hasattr(self.embedding_model, "encode"):
            vectors = self.embedding_model.encode(texts)
            return [list(map(float, v)) for v in vectors]

        vectors: List[List[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values: List[float] = []
            for i in range(self.embedding_dim):
                byte = digest[i % len(digest)]
                values.append((byte / 255.0) * 2 - 1)
            vectors.append(values)
        return vectors
