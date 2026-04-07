# RAG Dynamic Router - 完整实现指南

## 📌 项目概览

这是一个**多用户RAG系统，具有动态查询路由**的完整功能实现。系统智能地在向量搜索和知识图谱检索之间路由用户查询，以提供准确、可解释的答案。

**当前状态**: ✅ **完全实现** - 所有核心组件均已功能齐全

## 📂 项目结构

```
y:\wjw\
├── backend/                           # FastAPI 后端应用
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # ✅ FastAPI 应用工厂 - 完全实现
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py           # ✅ JWT 认证端点 - 完全实现
│   │   │   │   ├── query.py          # ✅ 查询端点 - 完全实现
│   │   │   │   ├── ingest.py         # ✅ 文档摄入端点 - 完全实现
│   │   │   │   └── admin.py          # ✅ 管理操作端点 - 完全实现
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # ✅ Pydantic 设置 - 完全实现
│   │   │   ├── security.py           # ✅ JWT 和密码工具 - 完全实现
│   │   │   ├── logging_setup.py      # ✅ 日志配置 - 完全实现
│   │   │   └── postgres.py           # PostgreSQL 数据库模式
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py            # Pydantic 数据结构
│   │   │   ├── dataclasses.py        # 数据类定义
│   │   │   └── response_models.py    # 响应模型
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── router_service.py     # ✅ 动态路由逻辑 - 完全实现
│   │   │   ├── vector_service.py     # ✅ 向量搜索（模拟） - 完全实现
│   │   │   ├── kg_service.py         # ✅ 知识图谱操作（模拟） - 完全实现
│   │   │   ├── reader_service.py     # ✅ 答案生成与重排 - 完全实现
│   │   │   └── ingest_service.py     # ✅ 文档摄入逻辑 - 完全实现
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── postgres.py           # PostgreSQL 客户端（模拟）
│   │   │   ├── vector_client.py      # 向量DB包装器（模拟）
│   │   │   └── neo4j_client.py       # Neo4j 客户端（模拟）
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── fixtures.py           # 分享的测试夹具
│   │       ├── test_services.py      # 服务层测试
│   │       ├── test_api.py           # API端点测试
│   │       └── test_integration.py   # 集成测试
│   ├── requirements.txt              # Python 依赖
│   ├── .env.example                  # 环境变量示例
│   └── Dockerfile                    # Docker 镜像
├── frontend/                          # Streamlit 前端应用
│   ├── streamlit_app/
│   │   ├── __init__.py
│   │   ├── app.py                    # ✅ 主应用与页面路由 - 完全实现
│   │   ├── auth.py                   # ✅ 认证UI - 完全实现
│   │   ├── query_ui.py               # ✅ 查询界面 - 完全实现
│   │   ├── utils.py                  # ✅ 工具函数与API处理 - 完全实现
│   │   └── pages/
│   │       ├── 01_Query.py           # 查询页面
│   │       ├── 02_History.py         # 历史记录页面
│   │       ├── 03_KB_Visualization.py # 知识库可视化页面
│   │       ├── 04_Metrics.py         # 指标页面
│   │       └── 05_Settings.py        # 设置页面
│   ├── requirements.txt              # 前端依赖
│   ├── .env.example                  # 环境变量示例
│   ├── .streamlit/
│   │   └── config.toml               # Streamlit 配置
│   └── Dockerfile                    # Docker 镜像
├── docker-compose.yml                # ✅ Docker Compose 开发配置 - 完全实现
├── kubernetes/                       # ✅ Kubernetes 生产配置 - 完全实现
│   ├── deployment.yaml               # 后端部署
│   ├── service.yaml                  # 服务暴露
│   ├── configmap.yaml                # 配置映射
│   └── postgres-statefulset.yaml     # PostgreSQL 有状态集
├── mvp.md                            # 原始 MVP 规范
└── README.md                         # 本文件
```

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Async**: AsyncIO, asyncpg
- **Databases**: SQLite（关系数据）, Neo4j（知识图谱）, ChromaDB（向量检索）
- **NLP**: sentence-transformers, spaCy (NER)
- **Authentication**: JWT, bcrypt
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: Streamlit (Python)
- **Visualization**: Plotly, Pyvis (graph visualization)
- **API Communication**: requests

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI 0.104.1 (异步Python)
- **数据库**: SQLite (关系)、Neo4j 5 (知识图谱)、ChromaDB (向量)
- **NLP**: sentence-transformers、spaCy (NER)
- **认证**: JWT (PyJWT)、bcrypt
- **异步**: 全内置 AsyncIO 支持
- **部署**: Docker、Kubernetes

### 前端
- **框架**: Streamlit 1.29.0 (Python)
- **API通信**: requests
- **可视化**: Plotly (图表)、内置 KG 可视化

### 基础设施
- **容器化**: Docker
- **编排**: Docker Compose (开发)、Kubernetes (生产)
- **日志**: 文件轮转和控制台输出

## 🚀 快速开始

### 方式1: 超薄本轻量模式（推荐）

```bash
# 1. 进入项目目录
cd y:\wjw

# 2. 先在电脑上启动本机 Neo4j 服务（非 Docker）
# Neo4j Browser: http://localhost:7474
# Bolt: bolt://localhost:7687
```

### 方式2: 手动运行前后端（本地）

#### 后端设置

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建 .env 文件（可选）
cp .env.example .env 2>/dev/null || true
# 默认已是 SQLite + Chroma + 本机 Neo4j，无需额外改动

# 5. 启动后端 (在项目根目录)
cd ..
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 前端设置（新终端）

```bash
# 1. 进入前端目录
cd frontend

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 创建 .env 文件
copy .env.example .env

# 5. 启动Streamlit应用
streamlit run streamlit_app/app.py
```

### 🔑 演示凭证

- **用户名**: `demo`
- **密码**: `demo123`

## 📊 核心功能

### 动态路由系统

系统根据查询特征自动选择最优检索策略：

| 策略 | 适用场景 | 输入特征 |
|------|--------|---------|
| **VECTOR_ONLY** | 纯文本查询 | 无实体 + 短查询 |
| **KG_ONLY** | 实体关系查询 | 高实体密度 |
| **KG_THEN_VECTOR** | 混合查询 | 中等实体 + 长查询 |
| **HYBRID_JOIN** | 综合查询 | 高置信度实体 |

### 关键决策因素

- **命名实体识别 (NER)**: 检测查询中的实体
- **查询特征提取**: 长度、词汇多样性等
- **历史性能**: 之前查询的路由效果
- **配置提示**: 用户可选择路由策略

## 📡 API 端点

### 认证
- `POST /api/v1/auth/login` - 用户登录，返回 JWT 令牌
- `POST /api/v1/auth/refresh` - 刷新过期令牌
- `POST /api/v1/auth/logout` - 用户登出

### 查询
- `POST /api/v1/query` - 提交查询并获取答案
  - 请求: `{ "query": "...", "session_id": "...", "top_k": 5, "router_hint": null }`
  - 响应: `{ "answer": "...", "evidence": [...], "router_decision": {...}, "latency_ms": 350 }`

### 文档摄入
- `POST /api/v1/ingest/documents` - 摄入文档
- `POST /api/v1/ingest/documents/file` - 上传 JSONL 文件
- `POST /api/v1/ingest/triples` - 摄入 KG 三元组
- `POST /api/v1/ingest/triples/file` - 上传三元组 JSONL 文件

### 管理
- `GET /api/v1/admin/route-strategies` - 获取可用路由策略
- `GET /api/v1/admin/metrics/query-distribution` - 查询分布指标
- `GET /api/v1/admin/metrics/performance` - 系统性能指标
- `GET /api/v1/admin/health` - 系统健康检查

## 🎨 前端功能

### 页面详情

1. **查询页面** (`Query`)
   - 文本框输入查询
   - 参数配置 (Top K、策略提示)
   - 实时答案显示
   - 证据来源展示
   - 查询历史快速访问

2. **历史记录** (`History`)
   - 查看所有历史查询
   - 按状态过滤（成功/失败）
   - 导出为 JSON
   - 批量清除历史

3. **知识图谱可视化** (`KG Visualization`)
   - 显示检索到的实体关系
   - 路径可视化
   - 置信度指示

4. **系统指标** (`Metrics`)
   - 查询统计（总数、成功率）
   - 路由策略分布 (柱状图)
   - 性能趋势 (延迟、成功率)
   - 实时监控数据

5. **设置** (`Settings`)
   - API 端点配置
   - 显示偏好设置
   - 会话信息
   - 系统信息与版本

## 💾 数据库架构

### PostgreSQL 表

```sql
-- 文档存储
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title VARCHAR(500),
    content TEXT,
    source VARCHAR(255),
    created_at TIMESTAMP,
    metadata JSONB
);

-- 文本块 (用于向量存储)
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    chunk_text TEXT,
    chunk_index INT,
    embedding VECTOR(384)  -- 向量维度
);

-- 查询历史
CREATE TABLE queries (
    id UUID PRIMARY KEY,
    user_id UUID,
    session_id VARCHAR(255),
    query_text TEXT,
    strategy VARCHAR(50),
    answer TEXT,
    latency_ms INT,
    created_at TIMESTAMP
);
```

### Neo4j 知识图谱

```
(Entity1)-[relationship:TYPE]->(Entity2)
```

**节点**: 实体（类型、属性）
**关系**: has_property、related_to、synonym_of 等
**属性**: confidence、source、provenance 等

### 向量数据库

- **支持**: Milvus、Chroma
- **维度**: 384 (sentence-transformers)
- **距离**: 余弦相似度
- **索引**: HNSW、IVF_FLAT

## 🧪 运行测试

```bash
# 安装测试依赖
cd backend
pip install -r requirements.txt

# 运行所有测试
pytest

# 运行特定测试
pytest app/tests/test_services.py -v

# 生成覆盖率报告
pytest --cov=app --cov-report=html
```

## 📈 系统架构
````

### Unit Tests
```bash
cd backend
pytest app/tests/test_router.py -v
```

### Integration Tests
```bash
pytest app/tests/test_endpoints.py -v
```

### With Coverage
```bash
pytest --cov=app app/tests/ -v
```

## Configuration

### Environment Variables
See `.env.example` files in `backend/` and `frontend/` directories.

Key settings:
- `DATABASE_URL` - PostgreSQL connection
- `NEO4J_URL` - Neo4j connection
- `VECTOR_DB_TYPE` - Vector DB choice (milvus, chroma, etc.)
- `SECRET_KEY` - JWT signing key
- `DEBUG` - Debug mode flag

### Database Setup
1. **PostgreSQL**: Automatically initialized by Docker/docker-compose
2. **Neo4j**: Web interface at http://localhost:7474
3. **Milvus**: Auto-initialization with default settings

## Deployment

### Docker Compose (Development)
```bash
docker-compose -f infra/docker-compose.yml up --build
```

### Kubernetes (Production)
```bash
kubectl apply -f infra/k8s/
```

Key K8s resources:
- Deployments: Backend, Frontend
- StatefulSet: Neo4j
- Services: Cluster IPs and LoadBalancer
- HPA: Auto-scaling based on CPU/memory

## Performance Considerations

- **Query Latency Target**: < 1 second (p95)
- **Parallel Retrieval**: Reduces latency for HYBRID_JOIN
- **Caching**: Redis-based query caching (optional)
- **Circuit Breaker**: Graceful degradation on service failures
- **Rate Limiting**: Prevents abuse

## Security Features

- **HTTPS/TLS**: Enabled via Ingress (K8s)
- **Authentication**: JWT tokens with refresh rotation
- **Password Security**: bcrypt hashing
- **Audit Logging**: All queries logged to PostgreSQL
- **Data Isolation**: User-level session separation
- **PII Protection**: Optional sensitive data redaction

## Monitoring & Logging

- **Application Logs**: Structured JSON logging
- **Metrics**: Prometheus-compatible endpoints
- **Query Analytics**: User dashboard with query distribution
- **Performance Metrics**: Latency P50/P95/P99, QPS

## Future Enhancements

1. Machine learning classifier for routing decisions
2. User feedback loop for continuous improvement
3. Advanced caching with Redis
4. Multi-language support
5. Custom embedding models
6. Federated learning for privacy
7. Advanced analytics dashboard
8. A/B testing framework

## Contributing

To add new features:
1. Create feature branch
2. Implement with tests
3. Update documentation
4. Submit pull request

## Support

For issues and questions:
- Check documentation in `docs/`
- Review API spec at `docs/api_spec.yaml`
- Check test examples in `backend/app/tests/`

## License

[ADD LICENSE INFORMATION]

---

**Last Updated**: January 2025
**Version**: 1.0.0
