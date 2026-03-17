# RAG 项目问题排查与修复记录

> 更新时间: 2026-03-17
> 维护人: 小王

---

## 🐛 问题1: 前端无法登录 (API 路径不匹配)

### 症状
- 前端登录失败，提示 `404 Not Found` 或 `Connection error`
- 错误信息: `HTTPConnectionPool(host='backend', port=8000): Max retries exceeded`

### 根因
前端 `secrets.toml` 配置的 API_ENDPOINT 包含 `/api/v1` 后缀，但后端实际路径没有这个前缀。

- 前端配置: `http://localhost:8000/api/v1/auth/login`
- 后端实际: `http://localhost:8000/auth/login`

### 修复方案

**1. 修改 `frontend/.streamlit/secrets.toml`:**
```toml
[general]
API_ENDPOINT = "http://localhost:8000"  # 去掉 /api/v1 后缀
```

**2. 代码无需修改 (auth.py 保持原样):**
```python
api_endpoint = utils.get_api_endpoint()
response = requests.post(
    f"{api_endpoint}/auth/login",  # 自动拼接正确路径
    ...
)
```

### 验证
- 访问 http://localhost:8502
- 使用 demo / demo123 登录
- 成功进入系统

---

## 🐛 问题2: Neo4j Browser 显示数据不全

### 症状
- Neo4j Browser 默认只显示 50 条记录

### 修复方案
在 Neo4j Browser 查询框中执行:
```cypher
MATCH (n)-[r]->(m) RETURN n,r,m
```
不添加 LIMIT 限制，显示全部 151 节点、271 关系。

---

## 📋 常用命令

### 查看容器状态
```bash
cd ~/Desktop/rag-kg/infra
docker-compose ps
```

### 查看 Neo4j 数据
```bash
# 节点数量
docker exec rag_neo4j cypher-shell -u neo4j -p testpass123 "MATCH (n) RETURN count(n)"

# 关系数量
docker exec rag_neo4j cypher-shell -u neo4j -p testpass123 "MATCH (a)-[r]->(b) RETURN count(r)"
```

### 查看 Milvus 向量
```python
from pymilvus import connections, Collection
connections.connect(host='localhost', port='19530')
from pymilvus import utility
collections = utility.list_collections()
for c in collections:
    coll = Collection(c)
    coll.load()
    print(f'{c}: {coll.num_entities}')
```

### 重启前端
```bash
cd ~/Desktop/rag-kg/frontend
streamlit run streamlit_app/app.py --server.port 8502
```

---

## 🔧 配置信息

| 服务 | 地址 | 账号 |
|------|------|------|
| Frontend | http://localhost:8502 | demo / demo123 |
| Backend | http://localhost:8000 | - |
| Neo4j | http://localhost:7474 | neo4j / testpass123 |
| Milvus | http://localhost:19530 | - |

---

## ✅ 系统状态 (2026-03-17)

| 组件 | 状态 | 数据量 |
|------|------|--------|
| rag_backend | ✅ healthy | - |
| rag_frontend | ✅ healthy | - |
| rag_postgres | ✅ running | - |
| rag_milvus | ✅ healthy | 246 条向量 |
| rag_neo4j | ✅ healthy | 151 节点, 271 关系 |
| rag_etcd | ✅ running | - |
