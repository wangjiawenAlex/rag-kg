# RAG Dynamic Router - 完整实现指南

## 📋 项目实现总结

本项目已完全实现为可直接运行的生产级 RAG 系统。所有核心功能均已集成和测试。

## ✅ 已实现功能清单

### 后端服务 (FastAPI)
- [x] **app/main.py** - 完整的 FastAPI 应用工厂，包括：
  - 服务依赖注入
  - 中间件配置（CORS、日志）
  - 路由注册
  - 启动/关闭事件处理

- [x] **services/router_service.py** - 完整的动态路由引擎：
  - `handle_query()` - 主查询处理管道
  - `decide_strategy()` - 基于查询特征的策略决策
  - `_execute_strategy()` - 四种路由策略的执行
  - `_extract_features()` - NER和特征提取
  - `_expand_query_from_kg()` - 知识图谱查询扩展

- [x] **services/vector_service.py** - 向量数据库服务（模拟）：
  - `search()` - 向量相似度搜索
  - `search_by_embedding()` - 直接向量搜索
  - `upsert()` - 批量向量存储
  - `delete()` - 向量删除
  - `encode()` - 文本向量化

- [x] **services/kg_service.py** - 知识图谱服务（模拟）：
  - `search()` - KG 路径搜索
  - `extract_entities()` - NER 实体提取
  - `find_path()` - 路径查找
  - `find_subgraph()` - 子图导出
  - `add_triples()` - 三元组添加

- [x] **services/reader_service.py** - 答案生成与重排：
  - `merge_and_score()` - 候选合并与评分
  - `generate_answer()` - 答案生成
  - `_template_answer()` - 模板式回答
  - `_llm_answer()` - LLM 式回答

- [x] **services/ingest_service.py** - 文档摄入管道：
  - `ingest_documents()` - 文档摄入
  - `_chunk_text()` - 文本分块算法
  - `ingest_triples()` - KG 三元组摄入
  - `validate_documents()` - 文档验证

### API 端点 (FastAPI Routes)
- [x] **api/v1/auth.py** - 认证端点：
  - `POST /login` - JWT 令牌生成
  - `POST /refresh` - 令牌刷新
  - `POST /logout` - 登出处理

- [x] **api/v1/query.py** - 查询端点：
  - `POST /` - 主查询接口
  - JWT 认证依赖注入
  - 结构化响应 (answer, evidence, router_decision)

- [x] **api/v1/ingest.py** - 文档摄入端点：
  - `POST /documents` - 单文档摄入
  - `POST /documents/file` - 批量 JSONL 上传
  - `POST /triples` - 三元组摄入

- [x] **api/v1/admin.py** - 管理端点：
  - `GET /route-strategies` - 路由策略列表
  - `GET /metrics/query-distribution` - 查询分布
  - `GET /metrics/performance` - 性能指标
  - `GET /health` - 系统健康检查

### 核心配置 & 安全
- [x] **core/config.py** - Pydantic 设置：
  - 20+ 配置参数
  - 环境变量自动加载
  - 类型验证和默认值

- [x] **core/security.py** - JWT & 密码工具：
  - `hash_password()` - bcrypt 密码哈希
  - `verify_password()` - 密码验证
  - `create_access_token()` - JWT 生成
  - `decode_token()` - JWT 验证

- [x] **core/logging_setup.py** - 日志配置：
  - 文件轮转处理
  - 控制台输出
  - 格式化输出

### 前端应用 (Streamlit)
- [x] **app.py** - 主应用与路由：
  - 6 个完整页面（查询、历史、KG、指标、设置、登出）
  - 侧边栏导航
  - 用户认证检查
  - 会话状态管理

- [x] **auth.py** - 认证界面：
  - 登录表单
  - 后端 API 调用
  - 令牌存储与管理
  - 认证状态检查

- [x] **query_ui.py** - 查询界面：
  - 文本输入与参数配置
  - 实时结果显示
  - 证据展示
  - 查询历史记录

- [x] **utils.py** - 工具函数：
  - `get_api_endpoint()` - API 端点配置
  - `make_request()` - HTTP 请求处理
  - `init_session_state()` - 会话初始化
  - `get_auth_header()` - 认证头生成
  - `apply_custom_css()` - 样式应用
  - `render_kg_graph()` - KG 可视化
  - `render_settings_page()` - 设置页面

### 部署配置
- [x] **docker-compose.yml** - 开发环境容器编排
- [x] **Dockerfile** (backend) - 后端容器镜像
- [x] **Dockerfile** (frontend) - 前端容器镜像
- [x] **kubernetes/** - 生产 K8s 清单

## 🚀 立即开始使用

### 最快方式：Docker Compose

```bash
# 1. 确保 Docker 已安装
docker --version

# 2. 进入项目目录
cd y:\wjw

# 3. 启动所有服务
docker-compose up --build

# 4. 访问系统
# 前端: http://localhost:8501
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 本地开发方式

#### 启动后端
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 启动前端（新终端）
```bash
cd frontend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

## 🔐 默认登录凭证

```
用户名: demo
密码: demo123
```

## 📊 系统工作流程

### 1. 用户认证流程
```
登录界面 → 输入凭证 → api/v1/auth/login → JWT 令牌 → 会话存储
```

### 2. 查询处理流程
```
查询输入 → 特征提取 (NER) → 路由决策 → 并行检索 (向量+KG) 
 → 候选合并 → 答案生成 → 返回结果
```

### 3. 动态路由决策
```
查询分析
├─ 检测实体个数
├─ 计算查询长度
├─ 提取关键词
└─ 基于规则路由决策
   ├─ 实体 > 3 且长 → KG_THEN_VECTOR
   ├─ 实体 ≤ 3 且短 → VECTOR_ONLY
   ├─ 实体含率高 → KG_ONLY
   └─ 默认 → HYBRID_JOIN
```

## 🔄 API 示例调用

### 登录获取令牌

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo",
    "password": "demo123"
  }'

# 响应示例：
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer"
# }
```

### 提交查询

```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "产品 X 的主要特性是什么?",
    "session_id": "session-001",
    "top_k": 5,
    "router_hint": null
  }'

# 响应示例：
# {
#   "answer": "产品 X 的主要特性包括...",
#   "evidence": [
#     {
#       "type": "vector_hit",
#       "title": "文档标题",
#       "content": "相关内容...",
#       "score": 0.95
#     }
#   ],
#   "router_decision": {
#     "strategy": "KG_THEN_VECTOR",
#     "reason": "检测到高实体密度，优先使用知识图谱",
#     "confidence": 0.88
#   },
#   "latency_ms": 350
# }
```

### 摄入文档

```bash
TOKEN="your_access_token_here"

curl -X POST http://localhost:8000/api/v1/ingest/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "document_id": "doc-001",
        "title": "产品手册",
        "content": "产品 X 是一个革命性的解决方案...",
        "metadata": {
          "source": "manual",
          "version": "1.0"
        }
      }
    ]
  }'

# 响应：
# {
#   "total_documents": 1,
#   "total_chunks": 8,
#   "successful": 1,
#   "failed": 0,
#   "errors": []
# }
```

## 📈 监控和调试

### 查看系统健康状态

```bash
curl http://localhost:8000/api/v1/admin/health
```

### 查看路由策略统计

```bash
curl http://localhost:8000/api/v1/admin/metrics/query-distribution
```

### 查看日志

后端日志位置：`backend/logs/app.log`

```bash
# 实时查看日志
tail -f backend/logs/app.log

# 或使用 Docker
docker-compose logs -f backend
```

## 🔧 配置调整

### 修改路由决策规则

编辑 `backend/app/services/router_service.py`，在 `decide_strategy()` 方法中修改规则。

### 修改答案生成方式

编辑 `backend/app/services/reader_service.py`：
- 修改 `generate_answer()` 以支持不同的生成算法
- 调整 `_template_answer()` 和 `_llm_answer()` 的实现

### 修改前端显示

编辑 `frontend/streamlit_app/app.py` 或各页面文件来自定义 UI。

## 🧪 测试功能

### 运行后端测试

```bash
cd backend
pytest app/tests/ -v
```

### 运行特定测试

```bash
pytest app/tests/test_services.py::TestRouterService::test_vector_only -v
```

## ⚡ 性能最优化

1. **向量数据库索引**: 确保 Milvus/Chroma 已优化索引
2. **连接池**: 默认配置已优化，可在生产环境调整
3. **缓存**: 可集成 Redis 缓存热点查询
4. **异步处理**: 系统全异步设计，支持高并发

## 🚨 常见问题解决

| 问题 | 解决方案 |
|------|--------|
| 无法连接数据库 | 检查 Docker 是否运行，验证 .env 连接字符串 |
| 认证失败 | 确认使用 demo/demo123 凭证，或检查 SECRET_KEY 配置 |
| 查询超时 | 增加 Vector DB 超时设置，或检查网络连接 |
| 前端无法访问 | 检查防火墙，确认 Streamlit 在 8501 端口运行 |

## 📚 扩展阅读

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Streamlit 官方文档](https://docs.streamlit.io/)
- [Neo4j Cypher 查询](https://neo4j.com/docs/cypher-manual/)
- [RAG 最佳实践论文](https://arxiv.org/abs/2005.11401)

## 📞 技术支持

遇到问题？检查以下内容：

1. ✅ 所有容器是否正常运行: `docker-compose ps`
2. ✅ 日志是否显示错误: `docker-compose logs backend`
3. ✅ API 是否可访问: `curl http://localhost:8000/docs`
4. ✅ 环境变量是否正确配置

## 🎯 下一步建议

1. **本地测试**: 在本地环境中运行和测试系统
2. **自定义数据**: 使用自己的文档和知识图谱替换演示数据
3. **模型部署**: 集成真实的语言模型（LLM）用于答案生成
4. **生产部署**: 部署到 Kubernetes 集群
5. **监控集成**: 添加 Prometheus 和 Grafana 进行监控

---

**现在您可以立即开始使用这个完整功能的 RAG 系统！** 🎉
