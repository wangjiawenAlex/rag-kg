"""
重新导入 RAG 数据（清理后重建）

- 清空 Neo4j，重新导入员工/部门/关系
- 删除 Milvus collection，重新导入 vector chunks（带 768 维 embeddings）
"""

import sys, os, json
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import torch

# ============ 配置 ============
MILVUS_HOST = "localhost"
MILVUS_PORT = "19530"
MILVUS_COLLECTION = "rag_chunks"
EMBEDDING_DIM = 768
EMBEDDING_MODEL = "BAAI/bge-base-zh-v1.5"

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "testpass123"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Handbook_Test_Dataset")

# ============ 1. 清理 Milvus ============
print("🗑️ 清理 Milvus collection...")
connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
if MILVUS_COLLECTION in utility.list_collections():
    c = Collection(MILVUS_COLLECTION)
    c.drop()
    print(f"  ✅ 已删除 {MILVUS_COLLECTION}")
else:
    print(f"  ℹ️ {MILVUS_COLLECTION} 不存在，跳过清理")

# ============ 2. 创建 Milvus Collection ============
print("\n📦 创建 Milvus collection（768 维）...")
fields = [
    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
    FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
]
schema = CollectionSchema(fields=fields, description="RAG chunks")
collection = Collection(name=MILVUS_COLLECTION, schema=schema)
print(f"  ✅ Collection '{MILVUS_COLLECTION}' 创建成功")

# 创建索引
print("  🔧 创建索引...")
index_params = {"metric_type": "COSINE", "index_type": "HNSW", "params": {"M": 16, "efConstruction": 128}}
collection.create_index(field_name="embedding", index_params=index_params)
print("  ✅ 索引创建成功")

# ============ 3. 加载 embedding 模型 ============
print("\n🤖 加载 embedding 模型...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"  使用设备: {device}")
model = SentenceTransformer(EMBEDDING_MODEL, device=device)
print(f"  ✅ 模型加载完成: {EMBEDDING_MODEL}")

# ============ 4. 导入 Vector Chunks ============
print("\n📥 导入 vector chunks（vector_blocks.json）...")
with open(os.path.join(DATA_DIR, "vector_blocks.json"), "r", encoding="utf-8") as f:
    blocks = json.load(f)
print(f"  共 {len(blocks)} 条数据")

entities = []
texts = []
ids = []

for block in blocks:
    text = f"{block['title']}\n{block['content']}"
    texts.append(text)
    ids.append(block["id"])
    entities.append({
        "id": block["id"],
        "category": block.get("category", ""),
        "title": block.get("title", ""),
    })

print(f"  📝 编码 {len(texts)} 条文本...")
embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)

print(f"  💾 写入 Milvus...")
rows = []
for i in range(len(texts)):
    rows.append({
        "id": ids[i],
        "text": texts[i],
        "metadata": json.dumps({"category": entities[i]["category"], "title": entities[i]["title"]}, ensure_ascii=False),
        "embedding": embeddings[i].tolist(),
    })

# 分批插入
batch_size = 50
for i in range(0, len(rows), batch_size):
    batch = rows[i:i+batch_size]
    collection.insert(batch)
    print(f"    写入 {min(i+batch_size, len(rows))}/{len(rows)} 条...")

collection.flush()
print(f"  ✅ 向量数据导入完成，共 {len(rows)} 条")

# ============ 5. 清理并导入 Neo4j ============
print("\n🗄️ 清理并重建 Neo4j 数据...")
with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
    with driver.session() as sess:
        # 清空所有节点和关系
        sess.run("MATCH (n) DETACH DELETE n")
        print("  ✅ Neo4j 清空完成")

        # 导入员工
        with open(os.path.join(DATA_DIR, "employees.json"), "r", encoding="utf-8") as f:
            employees = json.load(f)

        # 导入部门（去重）
        departments = set()
        for emp in employees:
            departments.add(emp["所属部门"])

        # 创建部门节点
        for dept in departments:
            sess.run("CREATE (d:Department {name: $name})", name=dept)
        print(f"  ✅ 创建 {len(departments)} 个部门节点")

        # 创建员工节点
        for emp in employees:
            sess.run("""
                CREATE (e:Entity {
                    emp_id: $emp_id,
                    name: $name,
                    gender: $gender,
                    age: $age,
                    education: $education,
                    major: $major,
                    school: $school,
                    entry_date: $entry_date,
                    regular_date: $regular_date,
                    trial_salary: $trial_salary,
                    regular_salary: $regular_salary,
                    current_salary: $current_salary,
                    salary_level: $salary_level,
                    performance: $performance,
                    department: $department,
                    team: $team,
                    office: $office,
                    seat: $seat,
                    hire_type: $hire_type,
                    contract_status: $contract_status,
                    insurance_base: $insurance_base
                })
                """,
                emp_id=emp["工号"],
                name=emp["姓名"],
                gender=emp["性别"],
                age=emp["年龄"],
                education=emp["学历"],
                major=emp["专业"],
                school=emp["毕业院校"],
                entry_date=emp["入职日期"],
                regular_date=emp.get("转正日期", ""),
                trial_salary=emp.get("试用期月薪", 0),
                regular_salary=emp.get("转正后月薪", 0),
                current_salary=emp.get("当前月薪", 0),
                salary_level=emp.get("薪资级别", ""),
                performance=emp.get("绩效等级", ""),
                department=emp["所属部门"],
                team=emp.get("所属团队", ""),
                office=emp.get("办公地点", ""),
                seat=emp.get("办公座位", ""),
                hire_type=emp.get("入职渠道", ""),
                contract_status=emp.get("劳动合同状态", ""),
                insurance_base=emp.get("五险一金缴纳基数", 0),
            )
            # 员工属于部门
            sess.run("""
                MATCH (e:Entity {emp_id: $emp_id})
                MATCH (d:Department {name: $dept})
                CREATE (e)-[:BELONGS_TO]->(d)
                """, emp_id=emp["工号"], dept=emp["所属部门"])
            # 员工薪资
            sess.run("""
                MATCH (e:Entity {emp_id: $emp_id})
                CREATE (s:Salary {salary: $salary})
                CREATE (e)-[:HAS_SALARY]->(s)
                """, emp_id=emp["工号"], salary=emp.get("当前月薪", 0))
        print(f"  ✅ 创建 {len(employees)} 个员工节点 + BELONGS_TO + HAS_SALARY 关系")

        # 导入汇报关系
        with open(os.path.join(DATA_DIR, "edges.json"), "r", encoding="utf-8") as f:
            edges = json.load(f)

        for edge in edges:
            sess.run("""
                MATCH (from:Entity {emp_id: $from_id})
                MATCH (to:Entity {emp_id: $to_id})
                CALL apoc.create.relationship(from, $rel, {}, to) YIELD rel
                RETURN rel
                """,
                from_id=edge["from"],
                to_id=edge["to"],
                rel=edge["relation"],
            )
        print(f"  ✅ 创建 {len(edges)} 条汇报关系")

        # 验证
        r = sess.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as cnt")
        print(f"  📊 Neo4j 统计: {[dict(_) for _ in r]}")
        r2 = sess.run("MATCH ()-[r]->() RETURN type(r) as rel, count(*) as cnt")
        print(f"  📊 关系统计: {[dict(_) for _ in r2]}")

# ============ 6. 验证 Milvus ============
print("\n🔍 验证 Milvus...")
collection.load()
print(f"  ✅ Milvus collection '{MILVUS_COLLECTION}' 已加载")
print(f"  Entities: {collection.num_entities}")

# 测试搜索
test_embedding = model.encode(["员工张三的部门"])[0].tolist()
results = collection.search(
    data=[test_embedding],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"ef": 64}},
    limit=3,
    output_fields=["id", "text", "metadata"],
)
print(f"  ✅ 测试搜索成功，返回 {len(results[0])} 条结果")

print("\n🎉 数据重建完成！")