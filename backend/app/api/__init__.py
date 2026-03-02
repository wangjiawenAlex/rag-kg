"""
Package initialization for API routers.
"""

from app.api.v1 import auth, query, ingest, admin

__all__ = ["auth", "query", "ingest", "admin"]
