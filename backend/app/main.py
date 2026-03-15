"""FastAPI application factory and configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, ingest, query
from app.core.config import Settings, get_settings
from app.core.logging_setup import configure_logging
from app.db.postgres import PostgresClient
from app.services.ingest_service import IngestService
from app.services.kg_service import KGService
from app.services.llm_service import create_llm_client
from app.services.reader_service import ReaderService, RerankerService
from app.services.router_service import RouterService
from app.services.vector_service import VectorService


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

    vector_service = VectorService(
        db_client={
            "url": settings.vector_db_url,
            "path": settings.vector_db_url,
            "collection_name": "rag_chunks",
            "embedding_dim": settings.embedding_dim,
        },
        embedding_model=None,
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
    app.state.rel_db = PostgresClient(settings.database_url)

    @app.on_event("startup")
    async def startup_event():
        try:
            await vector_service._ensure_ready()
            logger.info("Vector DB initialized (chroma/local)")
        except Exception as exc:
            logger.warning("Vector DB init failed: %s", exc)

        try:
            await app.state.rel_db.initialize()
            logger.info("SQLite initialized")
        except Exception as exc:
            logger.warning("SQLite init failed: %s", exc)

        try:
            await kg_service.connect()
            logger.info("Neo4j initialized")
        except Exception as exc:
            logger.warning("Neo4j init failed: %s", exc)

    @app.on_event("shutdown")
    async def shutdown_event():
        try:
            await app.state.rel_db.close()
        except Exception:
            pass

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
