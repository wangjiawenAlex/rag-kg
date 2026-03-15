"""
Test fixtures and utilities.

Shared test fixtures and helper functions.
"""

import pytest
from typing import Dict, List


@pytest.fixture
def sample_documents() -> List[Dict]:
    """Sample documents for testing."""
    return [
        {
            "doc_id": "doc-001",
            "title": "Dynamic Routing Overview",
            "text": "Dynamic routing is a technique...",
            "source": "paper",
            "metadata": {"created": "2025-01-01"}
        },
        {
            "doc_id": "doc-002",
            "title": "Knowledge Graph Basics",
            "text": "A knowledge graph is...",
            "source": "documentation",
            "metadata": {"created": "2025-01-02"}
        }
    ]


@pytest.fixture
def sample_triples() -> List[Dict]:
    """Sample knowledge graph triples."""
    return [
        {
            "id": "t-001",
            "subject": "dynamic routing",
            "predicate": "uses",
            "object": "vector search",
            "confidence": 0.9,
            "provenance": {"doc_id": "doc-001", "offset": 120}
        },
        {
            "id": "t-002",
            "subject": "knowledge graph",
            "predicate": "contains",
            "object": "entity",
            "confidence": 0.95,
            "provenance": {"doc_id": "doc-002", "offset": 45}
        }
    ]


@pytest.fixture
def sample_queries() -> List[Dict]:
    """Sample queries for testing."""
    return [
        {
            "query_id": "q-001",
            "query": "What is dynamic routing used for?",
            "expected_strategy": "HYBRID_JOIN",
            "expected_top_docs": ["doc-001::chunk-0"]
        },
        {
            "query_id": "q-002",
            "query": "Types of entities in knowledge graphs",
            "expected_strategy": "KG_THEN_VECTOR",
            "expected_top_docs": ["doc-002::chunk-1"]
        }
    ]


@pytest.fixture
def sample_user() -> Dict:
    """Sample user for testing."""
    return {
        "user_id": "user-001",
        "username": "testuser",
        "password": "testpass123",
        "role": "user"
    }


@pytest.fixture
def sample_session() -> Dict:
    """Sample session."""
    return {
        "session_id": "session-001",
        "user_id": "user-001",
        "created_at": "2025-01-01T00:00:00"
    }
