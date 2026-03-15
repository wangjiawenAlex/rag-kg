# RAG Dynamic Router - 快速开始文档

## 🚀 30秒快速开始

> 轻量本地运行目标：无 GPU、在线 LLM + 在线 Embedding API、SQLite + ChromaDB + 本地 Neo4j。

### 使用 Docker Compose

```bash
# 1. 确保 Docker 已安装并运行
docker --version

# 2. 进入项目目录
cd y:\wjw

# 3. 启动所有服务（只需一条命令）
docker-compose up --build

# 4. 等待消息 "Application startup complete"，然后访问：
# • 前端: http://localhost:8501
# • 后端: http://localhost:8000
# • API文档: http://localhost:8000/docs

# 登录凭证：
# 用户名: demo
# 密码: demo123
```

### 在浏览器中测试

1. **打开前端应用**
   ```
   http://localhost:8501
   ```

2. **使用演示凭证登录**
   - 用户名: `demo`
   - 密码: `demo123`

3. **试试查询**
   - 输入问题: "产品 X 的主要特性是什么？"
   - 点击 "Submit Query"
   - 查看答案、证据和路由决策

4. **探索功能**
   - **查询页面**: 提交新的查询
   - **历史记录**: 查看之前的查询
   - **KG 可视化**: 查看知识图谱路径
   - **系统指标**: 查看性能统计
   - **设置**: 配置 API 端点

## 💻 无 GPU 本地模式（推荐给超薄本）

```bash
# 1) 后端依赖（已去除 torch / sentence-transformers / milvus 等重依赖）
cd backend
pip install -r requirements.txt
copy .env.example .env
# 在 .env 中填写：LLM_API_KEY、EMBEDDING_API_KEY、NEO4J_PASSWORD

# 2) 启动后端
cd ..
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 3) 启动前端（新终端）
cd frontend
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

## 📡 使用 API

### 从命令行测试 API

```bash
# 1. 登录获取令牌
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}' | jq .access_token

# 复制返回的令牌，放入 TOKEN 变量
TOKEN="your_token_here"

# 2. 提交查询
curl -X POST http://localhost:8000/api/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query":"产品的特性",
    "session_id":"test-1",
    "top_k":5
  }' | jq .

# 3. 摄入文档
curl -X POST http://localhost:8000/api/v1/ingest/documents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents":[{
      "document_id":"doc-001",
      "title":"测试文档",
      "content":"关于产品的内容...",
      "metadata":{"source":"test"}
    }]
  }' | jq .
```

## 🧪 验证系统

### 方法1: 使用测试脚本

```bash
# 确保后端正在运行，然后：
python test_system.py

# 输出示例：
# ✓ 系统健康检查通过
# ✓ 登录成功，获得访问令牌
# ✓ 查询成功
# ✓ 文档摄入成功
# ✓ 获得 4 个路由策略
# ✓ 令牌刷新成功
# 总体: 6/6 测试通过
```

### 方法2: 访问 API 文档

启动后端后，访问交互式 API 文档：
```
http://localhost:8000/docs
```

在这里可以：
- 查看所有可用的 API 端点
- 直接在浏览器中测试端点
- 查看请求/响应格式

## 🎯 系统流程示例

### 一个完整的查询周期：

```
┌─────────────────────────────────────────────────┐
│  1. 用户在 Streamlit 中输入：                    │
│     "产品 X 有哪些高级功能?"                    │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  2. 前端发送请求到后端：                        │
│     POST /api/v1/query                          │
│     数据: {                                      │
│       "query": "...",                           │
│       "session_id": "...",                      │
│       "top_k": 5                                │
│     }                                           │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  3. 后端处理：                                  │
│     - NER: 提取实体 ["产品", "X", "功能"]      │
│     - 特征: 长度=8, 实体数=3, 信心度=0.85       │
│     - 决策: → KG_THEN_VECTOR                   │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  4. 知识图谱查询：                              │
│     找到路径: [Product-X] --has_feature->      │
│               [Feature1, Feature2, ...]         │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  5. 向量搜索扩展：                              │
│     编码查询向量                                │
│     搜索相似文本块                              │
│     返回Top 5相关文档                           │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  6. 候选合并：                                  │
│     合并 KG 路径 + 向量结果                     │
│     计算置信度分数                              │
│     排序 Top 3                                  │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  7. 答案生成：                                  │
│     使用模板/LLM 组合候选内容                   │
│     返回：                                      │
│       - answer: "产品X的高级功能包括..." │
│       - evidence: [{...}, {...}, ...]           │
│       - strategy: "KG_THEN_VECTOR"              │
│       - latency: 350ms                          │
└─────────────────────────────────────────────────┘
              │
              ↓
┌─────────────────────────────────────────────────┐
│  8. 用户收到结果                                │
│     - 显示答案                                  │
│     - 显示来源证据                              │
│     - 显示路由决策和延迟                        │
└─────────────────────────────────────────────────┘
```

## 🔄 常见工作流程

### 场景 1: 第一次使用

```
1. 启动系统 → docker-compose up
2. 打开 http://localhost:8501
3. 使用 demo/demo123 登录
4. 在查询框输入问题
5. 查看答案和证据
```

### 场景 2: 导入自己的文档

```
1. 使用文档摄入 API：
   curl -X POST http://localhost:8000/api/v1/ingest/documents \
     -H "Authorization: Bearer TOKEN" \
     -d '{"documents": [...]}'

2. 使用导入的文档提交查询

3. 查看系统如何路由和检索信息
```

### 场景 3: 监控系统性能

```
1. 定期查询 /admin/metrics/performance
2. 在前端 "Metrics" 页面查看统计
3. 检查日志 backend/logs/app.log
4. 根据需要调整参数
```

## 🐛 故障排除

### 无法启动 Docker

```bash
# 检查 Docker 是否运行
docker ps

# 查看错误日志
docker-compose logs

# 清空和重新启动
docker-compose down
docker-compose up --build
```

### 无法登录

```bash
# 确认后端运行
curl http://localhost:8000/docs

# 检查演示账户是否存在
# 应该能看到 auth/login 端点

# 检查错误日志
docker-compose logs backend | grep -i auth
```

### 查询很慢或超时

```bash
# 检查后端性能
curl http://localhost:8000/api/v1/admin/metrics/performance

# 查看日志中的瓶颈
docker-compose logs backend

# 尝试减少 top_k 参数
# 或增加查询超时
```

### 前端无法访问

```bash
# 检查 Streamlit 是否运行
curl http://localhost:8501

# 重启前端
docker-compose restart frontend

# 或手动启动
cd frontend
streamlit run streamlit_app/app.py
```

## 📦 项目包含内容

- ✅ **完整后端** - FastAPI 应用，包括所有服务
- ✅ **完整前端** - Streamlit 应用，包括所有页面
- ✅ **数据库模式** - SQLite 和 Neo4j 定义（向量库为 ChromaDB）
- ✅ **Docker 容器化** - 开发和生产配置
- ✅ **API 文档** - 完整的 API 规范
- ✅ **测试用例** - 系统验证脚本
- ✅ **示例数据** - 演示文档和查询

## 🎓 学习路径

1. **理解架构**
   - 阅读 mvp.md 了解需求
   - 查看 README.md 了解整体结构
   - 浏览代码了解实现细节

2. **运行演示**
   - 启动 Docker Compose
   - 使用前端提交查询
   - 观察系统如何路由和检索

3. **尝试定制**
   - 修改路由规则（router_service.py）
   - 更改答案生成逻辑（reader_service.py）
   - 自定义前端界面（app.py）

4. **部署到生产**
   - 配置 Kubernetes 清单
   - 设置监控和告警
   - 优化性能参数

## 🚀 下一步

- [ ] 运行系统验证脚本: `python test_system.py`
- [ ] 导入自己的文档数据
- [ ] 自定义路由策略
- [ ] 集成真实的 LLM 模型
- [ ] 选择 SQLite + Neo4j（本地）或按需扩展到生产数据库
- [ ] 配置生产监控

---

**就这么简单！现在开始使用 RAG Dynamic Router 吧！** 🎉

有问题？查看完整文档：
- 实现指南: IMPLEMENTATION_GUIDE.md
- API 文档: http://localhost:8000/docs
- 代码文档: 见各源文件中的注释
