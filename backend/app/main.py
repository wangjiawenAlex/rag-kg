"""
FastAPI application factory and configuration.

Initializes the FastAPI app with routers, middleware, and dependencies.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import auth, query, ingest, admin
from app.core.config import Settings, get_settings
from app.core.logging_setup import configure_logging, get_logger
from app.services.router_service import RouterService
from app.services.vector_service import VectorService
from app.services.kg_service import KGService
from app.services.reader_service import ReaderService, RerankerService
from app.services.ingest_service import IngestService
from app.services.llm_service import create_llm_client


def create_app(settings: Settings = None) -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Args:
        settings: Application settings
    
    Returns:
        Configured FastAPI app instance
    """
    if settings is None:
        settings = get_settings()
    
    # Initialize logging
    logger = configure_logging(settings.log_level, settings.log_file)
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-user RAG system with dynamic query routing"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    vector_service = VectorService(None, None)
    kg_service = KGService(None, None)
    reranker = RerankerService()
    
    # Initialize LLM client
    llm_client = create_llm_client(settings)
    reader = ReaderService(llm_client=llm_client)
    router_service = RouterService(vector_service, kg_service, reranker, reader)
    ingest_service = IngestService(vector_service, kg_service, None)
    
    # Store services in app state
    app.state.settings = settings
    app.state.logger = logger
    app.state.router_service = router_service
    app.state.ingest_service = ingest_service
    app.state.vector_service = vector_service
    app.state.kg_service = kg_service
    
    # Include routers
    app.include_router(auth.router)
    app.include_router(query.router)
    app.include_router(ingest.router)
    app.include_router(admin.router)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running"
        }
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
