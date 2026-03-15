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
    """Vector search service backed by Milvus."""

    def __init__(self, db_client=None, embedding_model=None, collection_name: str = "rag_chunks", embedding_dim: int = 384):
        """Initialize vector service."""
        self.db_client = db_client
        self.embedding_model = embedding_model
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        self._collection = None
        self._milvus_host = "localhost"
        self._milvus_port = "19530"
        self._milvus_alias = "default"

        if isinstance(db_client, dict):
            self.collection_name = db_client.get("collection_name", self.collection_name)
            self.embedding_dim = int(db_client.get("embedding_dim", self.embedding_dim))
            url = db_client.get("url")
            if url:
                parsed = urlparse(url)
                self._milvus_host = parsed.hostname or self._milvus_host
                self._milvus_port = str(parsed.port or self._milvus_port)
            self._milvus_host = db_client.get("host", self._milvus_host)
            self._milvus_port = str(db_client.get("port", self._milvus_port))

    async def _ensure_ready(self) -> None:
        """Ensure Milvus connection and collection are ready."""
        if self._collection is not None:
            return

        if self.db_client and hasattr(self.db_client, "search") and hasattr(self.db_client, "upsert"):
            # External adapter already provided.
            return

        from pymilvus import (
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            connections,
            utility,
        )

        def _connect_and_prepare():
            connections.connect(alias=self._milvus_alias, host=self._milvus_host, port=self._milvus_port)

            if not utility.has_collection(self.collection_name, using=self._milvus_alias):
                schema = CollectionSchema(
                    fields=[
                        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=256),
                        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                        FieldSchema(name="metadata", dtype=DataType.JSON),
                        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
                    ],
                    description="RAG chunks",
                    enable_dynamic_field=False,
                )
                collection = Collection(name=self.collection_name, schema=schema, using=self._milvus_alias)
                index_params = {
                    "index_type": "HNSW",
                    "metric_type": "COSINE",
                    "params": {"M": 8, "efConstruction": 64},
                }
                collection.create_index(field_name="embedding", index_params=index_params)
            else:
                collection = Collection(name=self.collection_name, using=self._milvus_alias)

            collection.load()
            return collection

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

        expr = None
        if filters and "doc_id" in filters:
            expr = f'metadata["doc_id"] == "{filters["doc_id"]}"'

        def _search():
            result = self._collection.search(
                data=[embedding],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"ef": 64}},
                limit=top_k,
                expr=expr,
                output_fields=["id", "text", "metadata"],
            )
            return result

        result = await asyncio.to_thread(_search)

        hits: List[VectorHit] = []
        for item in result[0]:
            entity = item.entity
            hits.append(
                VectorHit(
                    id=str(entity.get("id")),
                    text=entity.get("text", ""),
                    score=float(item.score),
                    metadata=entity.get("metadata", {}) or {},
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
            self._collection.upsert([ids, texts, metadata, vectors])
            self._collection.flush()

        await asyncio.to_thread(_upsert)
        return len(documents)

    async def delete(self, ids: List[str]) -> int:
        """Delete documents from vector database."""
        if not ids:
            return 0

        if self.db_client and hasattr(self.db_client, "delete"):
            return await self.db_client.delete(ids)

        await self._ensure_ready()
        quoted = ",".join([f'"{doc_id}"' for doc_id in ids])

        def _delete():
            self._collection.delete(expr=f"id in [{quoted}]")
            self._collection.flush()

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
