"""Vector database search service."""

from __future__ import annotations

import asyncio
import hashlib
import json
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
        self._db_type = "milvus"
        self._milvus_host = "localhost"
        self._milvus_port = "19530"
        self._milvus_alias = "default"
        self._chroma_path = "./data/chroma"
        self._chroma_client = None

        if isinstance(db_client, dict):
            self._db_type = str(db_client.get("db_type", self._db_type)).lower()
            self.collection_name = db_client.get("collection_name", self.collection_name)
            self.embedding_dim = int(db_client.get("embedding_dim", self.embedding_dim))
            url = db_client.get("url")
            if url:
                if self._db_type == "chroma":
                    self._chroma_path = url
                else:
                    parsed = urlparse(url)
                    self._milvus_host = parsed.hostname or self._milvus_host
                    self._milvus_port = str(parsed.port or self._milvus_port)
            self._milvus_host = db_client.get("host", self._milvus_host)
            self._milvus_port = str(db_client.get("port", self._milvus_port))
            self._chroma_path = db_client.get("path", self._chroma_path)

    async def _ensure_ready(self) -> None:
        """Ensure vector store connection and collection are ready."""
        if self._collection is not None:
            return

        if self.db_client and hasattr(self.db_client, "search") and hasattr(self.db_client, "upsert"):
            # External adapter already provided.
            return

        if self._db_type == "chroma":
            import chromadb

            def _connect_chroma():
                self._chroma_client = chromadb.PersistentClient(path=self._chroma_path)
                return self._chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )

            self._collection = await asyncio.to_thread(_connect_chroma)
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
            hits = []
            for item in rows:
                meta_str = item.get("metadata")
                if isinstance(meta_str, str):
                    try:
                        meta_val = json.loads(meta_str)
                    except Exception:
                        meta_val = {}
                else:
                    meta_val = meta_str or {}
                hits.append(VectorHit(
                    id=str(item.get("id", "")),
                    text=item.get("text", ""),
                    score=float(item.get("score", 0.0)),
                    metadata=meta_val,
                ))
            return hits

        await self._ensure_ready()

        expr = None
        if filters and "doc_id" in filters:
            expr = f'metadata["doc_id"] == "{filters["doc_id"]}"'

        def _search():
            if self._db_type == "chroma":
                chroma_result = self._collection.query(
                    query_embeddings=[embedding],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )
                return chroma_result
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
        if self._db_type == "chroma":
            ids = result.get("ids", [[]])[0]
            docs = result.get("documents", [[]])[0]
            metas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            for doc_id, text_val, meta_val, dist in zip(ids, docs, metas, distances):
                score = max(0.0, 1.0 - float(dist))
                hits.append(
                    VectorHit(
                        id=str(doc_id),
                        text=text_val or "",
                        score=score,
                        metadata=meta_val or {},
                    )
                )
            return hits

        for item in result[0]:
            entity = item.entity
            text_val = ""
            try:
                text_val = entity.get("text")
            except:
                pass
            id_val = ""
            try:
                id_val = entity.get("id")
            except:
                pass
            meta_val = {}
            try:
                raw_meta = entity.get("metadata")
                if isinstance(raw_meta, str):
                    try:
                        meta_val = json.loads(raw_meta)
                    except Exception:
                        meta_val = {}
                else:
                    meta_val = raw_meta or {}
            except Exception:
                pass
            hits.append(
                VectorHit(
                    id=str(id_val),
                    text=text_val,
                    score=float(item.score),
                    metadata=meta_val,
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
            if self._db_type == "chroma":
                self._collection.upsert(
                    ids=ids,
                    embeddings=vectors,
                    metadatas=metadata,
                    documents=texts,
                )
            else:
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
            if self._db_type == "chroma":
                self._collection.delete(ids=ids)
            else:
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
