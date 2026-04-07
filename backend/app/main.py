"""FastAPI application factory and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, ingest, query
from app.core.config import Settings, get_settings
from app.core.logging_setup import configure_logging
from app.services.ingest_service import IngestService
from app.services.kg_service import KGService
from app.services.llm_service import create_llm_client
from app.services.reader_service import ReaderService, RerankerService
from app.services.router_service import RouterService
from app.services.vector_service import VectorService


def load_embedding_model(model_name: str, logger=None):
    """Load sentence transformer embedding model with GPU support."""
    try:
        import os
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        
        from sentence_transformers import SentenceTransformer
        import torch
        # 使用 GPU 如果可用
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if logger:
            logger.info(f"Loading embedding model on device: {device}")
        return SentenceTransformer(model_name, device=device)
    except ImportError:
        if logger:
            logger.warning("sentence-transformers not installed, using dummy embeddings")
        return None
    except Exception as exc:
        if logger:
            logger.warning(f"Failed to load embedding model: {exc}")
        return None


def create_app(settings: Settings = None) -> FastAPI:
    """Create and configure FastAPI application."""
    if settings is None:
        settings = get_settings()

    logger = configure_logging(settings.log_level, settings.log_file)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-user RAG system with dynamic query routing",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load embedding model
    embedding_model = load_embedding_model(settings.embedding_model, logger)
    
    vector_service = VectorService(
        db_client={
            "db_type": settings.vector_db_type,
            "url": settings.vector_db_url,
            "collection_name": "rag_chunks",
            "embedding_dim": settings.embedding_dim,
        },
        embedding_model=embedding_model,
        collection_name="rag_chunks",
        embedding_dim=settings.embedding_dim,
    )

    kg_service = KGService(
        neo4j_client=None,
        ner_model=None,
        uri=settings.neo4j_url,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )

    reranker = RerankerService()
    llm_client = create_llm_client(settings)
    reader = ReaderService(llm_client=llm_client)
    router_service = RouterService(vector_service, kg_service, reranker, reader)
    ingest_service = IngestService(vector_service, kg_service, None)

    app.state.settings = settings
    app.state.logger = logger
    app.state.router_service = router_service
    app.state.ingest_service = ingest_service
    app.state.vector_service = vector_service
    app.state.kg_service = kg_service

    @app.on_event("startup")
    async def startup_event():
        try:
            await vector_service._ensure_ready()
            logger.info("%s vector store initialized", settings.vector_db_type)
        except Exception as exc:
            logger.warning("%s vector store init failed: %s", settings.vector_db_type, exc)

        try:
            await kg_service.connect()
            logger.info("Neo4j initialized")
        except Exception as exc:
            logger.warning("Neo4j init failed: %s", exc)

    @app.on_event("shutdown")
    async def shutdown_event():
        try:
            await kg_service.close()
        except Exception:
            pass

    app.include_router(auth.router)
    app.include_router(query.router)
    app.include_router(ingest.router)
    app.include_router(admin.router)

    @app.get("/")
    async def root():
        return {"name": settings.app_name, "version": settings.app_version, "status": "running"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": settings.app_version}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port, reload=settings.debug)
