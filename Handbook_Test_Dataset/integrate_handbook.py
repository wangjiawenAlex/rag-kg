import json

def format_markdown():
    with open("employees.json", "r", encoding="utf-8") as f:
        employees = json.load(f)
    with open("policies.json", "r", encoding="utf-8") as f:
        policies = json.load(f)
    with open("vector_blocks.json", "r", encoding="utf-8") as f:
        vector_blocks = json.load(f)
    with open("edges.json", "r", encoding="utf-8") as f:
        edges = json.load(f)

    md_content = "# 星辰科技员工手册 (测试版)\n\n"
    md_content += "> 本文档用于测试混合检测系统（向量检索 + 知识图谱检索）。\n\n"

    md_content += "## 1. 公司组织架构\n\n"
    md_content += "### 1.1 部门与团队\n"
    md_content += "| 部门 | 团队 |\n| --- | --- |\n"
    depts = {}
    for edge in edges:
        if edge["relation"] == "管辖":
            if edge["from"] not in depts: depts[edge["from"]] = []
            depts[edge["from"]].append(edge["to"])
    for d, ts in depts.items():
        md_content += f"| {d} | {', '.join(ts)} |\n"

    md_content += "\n## 2. 员工名录 (部分展示)\n\n"
    md_content += "| 工号 | 姓名 | 职位 | 部门 | 团队 | 办公地点 |\n"
    md_content += "| --- | --- | --- | --- | --- | --- |\n"
    for emp in employees[:10]:
        md_content += f"| {emp['工号']} | {emp['姓名']} | {emp['薪资级别']} | {emp['所属部门']} | {emp['所属团队']} | {emp['办公地点']} |\n"

    md_content += "\n## 3. 制度与流程 (详细条款)\n\n"
    for block in vector_blocks:
        md_content += f"### {block['title']} (ID: {block['id']})\n"
        md_content += f"**分类**: {block['category']}  \n"
        md_content += f"{block['content']}\n\n"

    md_content += "## 4. 知识图谱关系 (边列表示例)\n\n"
    md_content += "| 起点 (From) | 关系 (Relation) | 终点 (To) |\n"
    md_content += "| --- | --- | --- |\n"
    for edge in edges[:20]:
        md_content += f"| {edge['from']} | {edge['relation']} | {edge['to']} |\n"
    md_content += "... (总计 " + str(len(edges)) + " 条关系边)\n"

    with open("Employee_Handbook_Test_Data.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    print("员工手册 Markdown 文件生成成功。")

format_markdown()
