# 1 方案概览（目标）

目标：实现一个多用户系统，用户登录后可发起问答。后端通过 **动态路由器（Dynamic Router）** 在向量检索（RAG）和知识图谱（KG）检索之间智能调度（单独/串联/并行），最终通过 RAG + KG 的融合策略输出高准确度与可解释性的答案。系统要求可复现的实验日志与评估指标。

关键需求：

- 前后分离：Streamlit 前端（UI/交互）、FastAPI 后端（业务与微服务）
- 三库：Postgres（用户、日志、元数据）、VectorDB（向量检索）、Neo4j（知识图谱）
- 支持多用户登录、会话上下文、审计日志
- 动态路由策略可配置、可记录、可复现
- 输出同时包含“答案 + 证据片段 + KG 路径（可视化） + 路由决策理由”

------

# 2 架构（高层）

```
User (browser)
   │
Streamlit Frontend (独立服务)
   ├─ login / UI / KG可视化 / Evidence view
   │
   └─ requests (REST) --> FastAPI Backend (Auth + Router + Services)
                       ├─ Auth Service (JWT, sessions in Postgres)
                       ├─ Router Service (dynamic routing logic)
                       ├─ Retriever Vector Service (vector DB client)
                       ├─ Retriever KG Service (neo4j client)
                       ├─ Reranker / Reader Service (LLM / cross-encoder)
                       └─ Audit & Metrics -> Postgres / Prometheus
                           ├─ VectorDB (Milvus / Weaviate / Chroma / FAISS)
                           └─ Neo4j (KG)
```

部署建议（演示/生产）：

- Demo：Docker Compose（后端、streamlit、postgres、neo4j、milvus）
- 生产：Kubernetes + PersistentVolumes + Ingress + Secrets + HPA，外接 managed DB （可选）

------

# 3 API 设计（核心端点 — FastAPI）

主要路径简版（OpenAPI 风格）：

**认证**

- `POST /api/v1/auth/login`
   请求：

  ```
  {"username":"xxx","password":"yyy"}
  ```

  返回：

  ```
  {"access_token":"<jwt>","refresh_token":"<jwt>","expires_in":3600}
  ```

- `POST /api/v1/auth/refresh`：刷新 token

**查询**

- `POST /api/v1/query`
   请求：

  ```
  {
    "query": "问：动态路由什么时候优于纯向量检索？",
    "session_id": "string optional",
    "top_k": 5,
    "use_reader": true,
    "router_hint": null
  }
  ```

  返回（示例）:

  ```
  {
    "answer": "...",
    "evidence": [
      {"id":"doc-1::chunk-5","source":"vector","text":"...","score":0.92},
      {"id":"doc-7::chunk-1","source":"kg","path":["实体A","关系","实体B"],"score":0.87}
    ],
    "router_decision": {
      "strategy":"KG_THEN_VECTOR",
      "reason":"contains named entity & expects interpretable path"
    },
    "latency_ms": 420
  }
  ```

**管理 / 数据入库**

- `POST /api/v1/ingest/documents` 批量入文档（返回分片数量、失败列表）
- `POST /api/v1/ingest/triples` 批量上传三元组
- `GET /api/v1/admin/route-strategies` 管理路由策略（仅管理员）

**监控 / 日志**

- `GET /api/v1/metrics/query-distribution` （返回路由分布、平均延迟）

------

# 4 目录与逐文件职责（工程交付清单）

```
/project-root
├─ frontend/
│   ├─ streamlit_app/
│   │   ├─ app.py                  # Streamlit 主入口（页面布局与交互）
│   │   ├─ auth.py                 # 登录控件（调用 backend /auth）
│   │   ├─ query_ui.py             # 查询主界面、证据面板、KG 可视化
│   │   └─ utils.py                # token 存取、样式、图形渲染工具
│   └─ Dockerfile
├─ backend/
│   ├─ app/
│   │   ├─ main.py                 # FastAPI 应用工厂（依赖注入）
│   │   ├─ api/
│   │   │   ├─ v1/
│   │   │   │   ├─ auth.py
│   │   │   │   ├─ query.py
│   │   │   │   ├─ ingest.py
│   │   │   │   └─ admin.py
│   │   ├─ core/
│   │   │   ├─ config.py
│   │   │   ├─ security.py         # JWT, password hashing
│   │   │   └─ logging_setup.py
│   │   ├─ services/
│   │   │   ├─ router_service.py   # 动态路由主逻辑
│   │   │   ├─ vector_service.py   # 向量检索封装
│   │   │   ├─ kg_service.py       # neo4j 查询封装
│   │   │   ├─ reader_service.py   # LLM / reranker
│   │   │   └─ ingest_service.py
│   │   ├─ db/
│   │   │   ├─ postgres.py         # SQLAlchemy / asyncpg 客户端
│   │   │   ├─ vector_client.py    # Milvus / Chroma client wrapper
│   │   │   └─ neo4j_client.py
│   │   └─ tests/
│   │       ├─ test_router.py
│   │       ├─ test_endpoints.py
│   │       └─ fixtures/
│   └─ Dockerfile
├─ infra/
│   ├─ docker-compose.yml
│   ├─ k8s/
│   │   ├─ backend-deploy.yaml
│   │   ├─ frontend-deploy.yaml
│   │   └─ neo4j-statefulset.yaml
├─ docs/
│   ├─ architecture.md
│   └─ api_spec.yaml
└─ testdata/
    ├─ docs.jsonl
    ├─ triples.jsonl
    └─ queries.jsonl
```

下面对关键文件给出更细职责和建议实现细节（含函数签名）：

### backend/app/main.py

- create_app()：注入 DB clients、router_service、注册 APIRouter、添加中间件（CORS、Auth）。
- 启动时做 readiness checks（DB 可达性）。

### backend/app/api/v1/auth.py

- `POST /auth/login`：验证用户名/密码（bcrypt），返回 JWT。
- `POST /auth/refresh`：refresh token。

### backend/app/api/v1/query.py

- `POST /query`：带 Authorization header（Bearer token）。
- 调用 `router_service.handle_query(user_id, session_id, query, options)` 并返回结构化结果。
- 在请求/响应中写审计日志到 Postgres（query_logs 表）。

### backend/app/services/router_service.py

核心：根据 Query 特征（实体、长度、疑问词、embedding 相似性分布、历史成功策略）输出路由策略并执行。

主要函数与伪代码：

```
class RouterService:
    async def handle_query(self, user_id: str, session_id: Optional[str], query: str, top_k: int=5):
        start = now()
        features = await self._extract_features(query)
        strategy, reason = self.decide_strategy(features)
        # 调用对应检索路径
        if strategy == "VECTOR_ONLY":
            vector_hits = await self.vector_service.search(query, top_k)
            kg_paths = []
        elif strategy == "KG_ONLY":
            kg_paths = await self.kg_service.search(query, top_k)
            vector_hits = []
        elif strategy == "KG_THEN_VECTOR":
            kg_paths = await self.kg_service.search(query, top_k_kg)
            # optionally transform kg_paths -> query expansion -> vector search
            expanded_q = self._expand_query_from_kg(kg_paths)
            vector_hits = await self.vector_service.search(expanded_q, top_k)
        else: # HYBRID_JOIN
            # parallel
            vector_hits, kg_paths = await asyncio.gather(
                self.vector_service.search(query, top_k),
                self.kg_service.search(query, top_k)
            )
        # merge + rerank
        candidates = self.reranker.merge_and_score(vector_hits, kg_paths, query)
        answer = await self.reader.generate_answer(query, candidates)
        # log and return
```

`decide_strategy(features)` 的可用实现：

- 初期：规则集（entity present → KG preferred；long descriptive query → vector preferred；explicit explainable → KG）
- 中期：轻量分类器（logistic / xgboost）用历史 query->best_strategy 标签训练
- 始终保留 fallback：若某库不可用则降级到另一个策略并记录

### backend/app/services/vector_service.py

- `async search(query_or_embedding, top_k) -> List[Hit]`
- `async upsert(doc_chunks)`, `async delete(ids)`
- 封装 embedding 生成（sentence-transformers 或外部 API），批量化与缓存。

返回 Hit 格式：

```
{
  "id":"doc-1::chunk-4",
  "text":"...",
  "metadata":{"doc_id":"doc-1","chunk_index":4,"source":"paper"},
  "score":0.912
}
```

### backend/app/services/kg_service.py

- `async search(query, top_k) -> List[PathResult]`
- 使用 NER -> 映射到实体 -> 用 Cypher 找 k-hop 子图或 shortest path
- 返回 PathResult：

```
{
  "path_id":"path-123",
  "triples":[{"s":"A","p":"rel","o":"B"},...],
  "confidence":0.87,
  "provenance":[{"doc_id":"doc-1","offset":120}]
}
```

### backend/app/services/reranker.py

- `merge_and_score(vector_hits, kg_paths, query) -> List[Candidate]`
- 可使用 cross-encoder（重新计算 query-candidate score）或简单启发式（优先KG路径 -> vector）
- 输出带统一置信度 `score` 和 `source` 标签

### backend/app/services/reader_service.py

- `generate_answer(query, candidates, mode="concise") -> {"answer":str,"explain":str,"sources":[...]}`
- 支持：模板合成（无 LLM）、调用 LLM API（需要配置及隐私说明）

------

# 5 数据结构与数据库 DDL / Schema

## Postgres（关系型） — 用户、会话、查询日志、doc metadata

示例 DDL（Postgres）：

```
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  created_at timestamptz DEFAULT now()
);

CREATE TABLE sessions (
  session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id),
  created_at timestamptz DEFAULT now(),
  last_active_at timestamptz
);

CREATE TABLE query_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID,
  session_id UUID,
  query_text TEXT,
  router_decision JSONB,
  latency_ms INT,
  result_summary JSONB,
  created_at timestamptz DEFAULT now()
);

CREATE TABLE documents_meta (
  doc_id TEXT PRIMARY KEY,
  title TEXT,
  source TEXT,
  published_at DATE,
  metadata JSONB
);
```

## 向量数据库（Milvus / Chroma / FAISS）

向量 store 字段（每一个 chunk 的记录）：

- `id` string (doc_id::chunk_index)
- `embedding` float[] (向量维度 e.g. 768/1536)
- `text` text (chunk 文本或预览)
- `doc_id` string
- `chunk_index` int
- `metadata` json (source, title, created_at, offsets)

（Milvus/Weaviate 使用其 native schema；如果用 Chroma/FAISS：使用 sqlite/Postgres 保存 metadata 并把 embeddings 存在 FAISS）

示例向量元数据 JSON：

```
{
  "id":"doc-0001::chunk-5",
  "doc_id":"doc-0001",
  "chunk_index":5,
  "text_preview":"动态路由可以...",
  "source":"paper",
  "created_at":"2025-10-01"
}
```

## 图数据库（Neo4j）模型

节点 Label：

- `:Entity {name, types:[...], aliases:[...], provenance:[doc_id,...]}`
- `:DocumentSegment {doc_id, chunk_index, text, metadata}`

关系 Types：

- `:MENTIONS` (Entity)-[:MENTIONS]->(DocumentSegment)
- `:RELATED_TO` (Entity)-[:RELATED_TO {rel_type,confidence,source_doc}]->(Entity)
- `:EVIDENCE_FOR` (DocumentSegment)-[:EVIDENCE_FOR]->(Entity)  （可反向）

示例 Cypher 插入：

```
MERGE (e:Entity {name:$entity_name})
MERGE (d:DocumentSegment {doc_id:$doc_id, chunk_index:$chunk_index})
MERGE (e)-[:MENTIONS {offset:$offset,source:$source}]->(d)
```

------

# 6 流程详解（用户：登录 -> 问答 的完整调用链）

1. 前端（Streamlit）通过 `/auth/login` 登录，存储 access_token（short-lived）与 refresh_token（httpOnly cookie 或本地存储）。
2. 前端在用户发起 query 时调用 `POST /api/v1/query`，带 Authorization header。
3. 后端 `router_service`：
   - 抽取特征：NER、疑问类型、query embedding、上下文（session 历史）。
   - 决策：`decide_strategy(features)`（规则或 classifier）。
   - 执行：按策略调用 `kg_service` / `vector_service`（并行或串联）。
   - `reranker` 合并候选，调用 `reader` 生成回答（或模板拼接）。
   - 返回结构化结果，写 `query_logs` 到 Postgres，更新 metrics。
4. 前端接到结果，渲染：
   - 答案文本
   - 证据列表（按 score）
   - KG 路径（Graph 可视化）
   - 路由决策（策略+原因）
5. 用户可对结果作评价（帮助收集训练数据用于改进 router/ reranker）。

------

# 7 前端（Streamlit）实现要点（文件与函数）

`frontend/streamlit_app/app.py`（主流程）：

- 登录页：`auth.login()` 调用后端 `/auth/login`，存 token。
- 主页面：输入框、历史对话、按键“查询”。
- 异步或同步请求：streamlit 只支持同步请求，建议使用 `requests`（后端做短超时）。
- 证据展示：左列向量证据，右列 KG 路径（用 `st.graphviz_chart` 或 `pyvis`渲染）。
- 路由分解：展示 `router_decision.reason`，并提供 “显示原始候选” 切换。
- 管理面板（仅 admin 登录可见）：ingest 上传、重建索引、查看 query logs（调用 admin APIs）。

安全提示：

- 前端不直接访问 DB，只调用后端 API。
- token 可以存在 Streamlit 的 session_state（注意泄露风险），生产建议 httpOnly cookie +反向代理。

------

# 8 测试数据与示例（testdata）

**docs.jsonl**（文本语料，每行 JSON）：

```
{"doc_id":"doc-0001","title":"动态路由综述","text":"动态路由是一种...", "source":"paper"}
```

**triples.jsonl**（KG 三元组）：

```
{"id":"t-0001","subject":"动态路由","predicate":"应用于","object":"混合检索","provenance":{"doc_id":"doc-0001","offset":120},"confidence":0.9}
```

**queries.jsonl**（回归测试）：

```
{"query_id":"q-001","query":"什么时候用知识图谱？","expected_strategy":"KG_THEN_VECTOR","expected_top_docs":["doc-0001::chunk-2"]}
```

------

# 9 部署（Docker Compose）示例（核心片段）

```
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:example@postgres:5432/ragdb
      - NEO4J_URL=bolt://neo4j:7687
    depends_on:
      - postgres
      - neo4j
      - milvus
  frontend:
    build: ./frontend
    command: streamlit run app.py --server.port 8501
    ports:
      - "8501:8501"
    depends_on:
      - backend
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: example
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/test
    ports:
      - "7474:7474"
      - "7687:7687"
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
```

启动：`docker-compose up --build`

生产（K8s）建议：

- 后端部署作 Deployment + Service + HPA
- Neo4j 用 StatefulSet + PV
- Milvus/Vector DB 根据选型（managed 或 k8s helm charts）
- Ingress + TLS
- 使用 Secret 管理 DB 密码

------

# 10 性能/可用性/容错策略

- Circuit breaker：在 router 中对 vector/neo4j 调用设置超时与降级（例如 300ms 超时则标记不可用并切换策略）。
- 缓存：query->answer cache（Redis）短时缓存（提高 QPS）
- 并行化：HYBRID_JOIN 使用 asyncio.gather 并行检索
- 扩展：将 vector 服务与 reader 服务拆成独立 microservice（K8s 便于横向扩容）

------

# 11 评估指标 & A/B 实验（证明创新点）

实验设计：使用标注测试集（N ≥ 100）

对比策略：

- Baseline A：VECTOR_ONLY（top-K + reader）
- Baseline B：KG_ONLY（path-based answer）
- Ours：动态路由（本系统）

指标：

- Accuracy / EM（exact match on answer）
- Evidence Precision@k（候选证据含正确证据的比例）
- Explainability score（人工打分 1–5）
- Latency P50/P95/P99
- Average compute cost (向量 search 调用次数, KG query 次数)

收集日志：每次 query 将决策、被调 API、耗时写入 `query_logs` 以便离线分析。

------

# 12 安全与隐私

- 所有 API 使用 HTTPS（Ingress/TLS）
- 密码存储用 bcrypt
- Token 使用 JWT（短期） + refresh token（可选）
- 记录审计日志且对敏感字段做脱敏（PII）
- 如果使用第三方 LLM/Embedding 服务：在系统中明确标注并提供 opt-out，写入隐私策略

------

# 13 测试计划（单元 / 集成 / E2E）

单元测试要点：

- Router.decide_strategy 在边界输入（含 entity/无 entity/长短 query）应返回期望策略
- VectorService.search 在给定 embeddings 下返回正确排序（固定小数据）
- KGService.search 能够检索到预期 path（在 test neo4j fixture 中）

集成测试：

- 本地 docker-compose 环境下执行 `POST /api/v1/ingest` -> `POST /api/v1/query`，对比预期 top docs / router decision（参考 testdata/queries.jsonl）

E2E（答辩演示）：

- 提供 `run_demo.sh`：自动启 docker-compose，注入 testdata，运行 few queries 并生成评估报告 `results.csv`。

------

# 14 交付物清单（你会得到的设计交付包）

1. `docs/architecture.md`（包含 sequence diagrams、component diagrams）
2. `docs/api_spec.yaml`（完整 OpenAPI）
3. `backend/` 文件骨架（文件说明 + 函数签名）
4. `frontend/streamlit_app/app.py` 模板（完全可运行的 demo 页面）
5. `infra/docker-compose.yml`（可一键起环境）
6. `testdata/`（docs.jsonl, triples.jsonl, queries.jsonl 示例）
7. `evaluation/`（A/B 脚本 + 指标表格模板）
8. `README.md`（部署与本地演示步骤）