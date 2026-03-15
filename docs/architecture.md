# RAG Dynamic Router - Architecture

## System Overview

The RAG Dynamic Router system is a multi-user question-answering platform that intelligently routes queries between vector-based and knowledge-graph-based retrieval strategies. The system is designed to provide accurate answers with explainable evidence.

## Architecture Components

### Frontend Layer (Streamlit)

- User authentication and session management
- Query interface with real-time response display
- Evidence and knowledge graph visualization
- Admin dashboard for data management

### API Layer (FastAPI)

- RESTful API endpoints following OpenAPI specification
- Authentication with JWT tokens
- Request validation and error handling
- Rate limiting and security measures

### Core Services

#### Router Service
- Dynamically selects retrieval strategy based on query analysis
- Supports: VECTOR_ONLY, KG_ONLY, KG_THEN_VECTOR, HYBRID_JOIN
- Extracts features: entities, query type, length, embedding
- Decides strategy using rules or ML classifier

#### Vector Service
- Integrates with vector databases (Milvus, Chroma, etc.)
- Handles text embedding generation
- Performs similarity search
- Manages vector-to-document mapping

#### Knowledge Graph Service
- Neo4j integration for entity and relationship storage
- Named Entity Recognition (NER) for query analysis
- Path finding and relationship traversal
- Subgraph extraction around entities

#### Reader Service
- Reranks candidate evidence using cross-encoders
- Generates final answers via template or LLM
- Compiles structured response with sources

### Data Layer

**PostgreSQL**
- User management and authentication
- Session tracking
- Query audit logs
- Document metadata

**Vector Database (Milvus/Chroma)**
- Document embeddings and chunks
- Fast similarity search
- Metadata indexing

**Neo4j**
- Entity definitions and properties
- Relationship definitions
- Provenance links to source documents

## Data Flow

1. User submits query via Streamlit frontend
2. Frontend sends authenticated request to backend API
3. Router Service receives request:
   - Extracts features (entities, type, embedding)
   - Decides routing strategy
   - Executes retrieval (may be parallel or sequential)
4. Results are merged and reranked
5. Reader generates final answer
6. Response is logged and returned to frontend
7. Frontend renders answer with evidence and metadata

## Deployment Strategies

### Development (Docker Compose)
- Single-node deployment
- All services in containers
- Suitable for testing and demos
- Uses embedded or small-scale databases

### Production (Kubernetes)
- Scalable microservices architecture
- Separate deployments for each component
- Horizontal Pod Autoscaling (HPA)
- Persistent volumes for data
- Ingress for external access
- Secrets management for credentials

## Security Considerations

- HTTPS/TLS for all communications
- JWT tokens for API authentication
- Password hashing with bcrypt
- Audit logging for compliance
- PII handling and data privacy
- Optional integration with external services

## Performance Characteristics

- Sub-second latency target for query processing
- Parallel retrieval for HYBRID_JOIN strategy
- Caching layer for frequent queries
- Circuit breakers for fault tolerance
- Rate limiting to prevent abuse
