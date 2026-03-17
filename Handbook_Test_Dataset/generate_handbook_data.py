import json
import random
from datetime import datetime, timedelta

# 配置信息
COMPANIES = ["星辰科技"]
DEPARTMENTS = ["技术部", "销售部", "市场部", "人事部", "财务部", "运营部", "产品部", "客服部"]
TEAMS = {
    "技术部": ["前端组", "后端组", "测试组", "AI组"],
    "销售部": ["销售一组", "销售二组", "大客户部"],
    "市场部": ["品牌组", "公关组"],
    "人事部": ["招聘组", "薪酬组"],
    "财务部": ["核算组", "审计组"],
    "运营部": ["内容组"],
    "产品部": ["产品设计组"],
    "客服部": ["售后支持组"]
}
POSITIONS = ["CEO", "CTO", "总监", "经理", "主管", "高级工程师", "工程师", "专员"]
LOCATIONS = ["北京总部", "上海分部", "深圳分部", "杭州办公室", "成都办公室", "广州办公室", "南京办公室", "武汉办公室", "西安办公室", "苏州办公室"]
DEVICES = ["办公电脑", "打印机", "会议室投影仪", "门禁卡", "服务器", "路由器", "交换机", "防火墙", "存储阵列", "负载均衡器"]

# 生成员工数据
def generate_employees(count=50):
    employees = []
    for i in range(1, count + 1):
        emp_id = f"EMP{i:03d}"
        dept = random.choice(DEPARTMENTS)
        team = random.choice(TEAMS[dept])
        pos = random.choice(POSITIONS)
        level = f"P{random.randint(3, 9)}"
        perf = random.choice(["A", "B", "C", "S"])
        
        # 入职日期在 2018 到 2024 之间
        start_date = datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2200))
        probation_salary = random.randint(15000, 30000)
        regular_salary = int(probation_salary * 1.2)
        current_salary = int(regular_salary * (1.1 ** (2025 - start_date.year)))
        
        emp = {
            "工号": emp_id,
            "姓名": f"员工{i}",
            "性别": random.choice(["男", "女"]),
            "年龄": random.randint(22, 45),
            "学历": random.choice(["本科", "硕士", "博士"]),
            "专业": random.choice(["计算机科学", "电子工程", "市场营销", "人力资源", "会计学", "工商管理"]),
            "毕业院校": random.choice(["清华大学", "北京大学", "复旦大学", "上海交通大学", "浙江大学"]),
            "入职日期": start_date.strftime("%Y-%m-%d"),
            "转正日期": (start_date + timedelta(days=90)).strftime("%Y-%m-%d"),
            "试用期月薪": probation_salary,
            "转正后月薪": regular_salary,
            "当前月薪": current_salary,
            "薪资级别": level,
            "绩效等级": perf,
            "所属部门": dept,
            "所属团队": team,
            "直属上级": f"EMP{max(1, i-5):03d}", # 简化逻辑：上级是编号较小的员工
            "下属": [f"EMP{i+j:03d}" for j in range(1, 3) if i+j <= count],
            "办公地点": random.choice(LOCATIONS),
            "办公座位": f"{random.randint(1, 5)}-{random.randint(1, 50)}",
            "入职渠道": random.choice(["社招", "校招", "内推"]),
            "劳动合同状态": "生效中",
            "合同到期日": (start_date + timedelta(days=365*3)).strftime("%Y-%m-%d"),
            "五险一金缴纳基数": current_salary,
            "紧急联系人": f"联系人{i} 138{random.randint(10000000, 99999999)}",
            "背景调查": "已通过",
            "离职": None
        }
        employees.append(emp)
    return employees

# 生成制度数据
def generate_policies(count=25):
    policies = []
    names = ["年假管理制度", "加班调休制度", "报销管理制度", "绩效考核制度", "晋升通道管理", "差旅补贴标准", "办公用品申领规范", "信息安全管理制度", "员工行为准则", "远程办公管理办法"]
    for i in range(1, count + 1):
        name = names[i % len(names)] + f"_{i}"
        policy = {
            "制度编号": f"HR-2024-{i:03d}",
            "制度名称": name,
            "版本": f"v{random.randint(1, 3)}.{random.randint(0, 9)}",
            "状态": "生效中",
            "制定人": f"人事部-经理{random.randint(1, 5)}",
            "审批人": "CEO-张总",
            "制定日期": "2024-01-01",
            "生效日期": "2024-01-01",
            "最近修订日期": "2025-06-15",
            "修订原因": "业务调整及法规更新",
            "关联制度": [f"HR-2024-{random.randint(1, count):03d}" for _ in range(2)],
            "适用对象": "全体正式员工",
            "不适用对象": "实习生、外包人员",
            "关键词": [name[:2], "制度", "规范"],
            "相关流程": [f"PROC-{random.randint(1, 20):03d}"],
            "相关表单": [f"FORM-{random.randint(1, 15):03d}"]
        }
        policies.append(policy)
    return policies

# 生成关系边 (Knowledge Graph Edges)
def generate_edges(employees, policies):
    edges = []
    
    # 1. 上下级汇报 (50条)
    for emp in employees:
        if emp["工号"] != "EMP001":
            edges.append({"from": emp["工号"], "to": emp["直属上级"], "relation": "汇报给"})
            
    # 2. 部门-团队所属 (15条)
    for dept, teams in TEAMS.items():
        for team in teams:
            edges.append({"from": dept, "to": team, "relation": "管辖"})
            
    # 3. 员工-制度关联 (80条)
    for _ in range(80):
        emp = random.choice(employees)
        pol = random.choice(policies)
        edges.append({"from": emp["工号"], "to": pol["制度编号"], "relation": "适用"})

    # 4. 制度-流程引用 (50条)
    for pol in policies:
        edges.append({"from": pol["制度编号"], "to": f"PROC-{random.randint(1, 20):03d}", "relation": "引用"})
        if len(edges) >= 195 + 50: break # 简单计数

    # 5. 制度-制度关联 (40条)
    for _ in range(40):
        p1 = random.choice(policies)
        p2 = random.choice(policies)
        if p1 != p2:
            edges.append({"from": p1["制度编号"], "to": p2["制度编号"], "relation": "关联"})

    # 6. 流程-表单使用 (30条)
    for i in range(1, 21):
        edges.append({"from": f"PROC-{i:03d}", "to": f"FORM-{random.randint(1, 15):03d}", "relation": "使用"})

    # 7. 员工-设备领用 (30条)
    for _ in range(30):
        emp = random.choice(employees)
        dev = f"DEV-{random.randint(1, 20):03d}"
        edges.append({"from": emp["工号"], "to": dev, "relation": "领用"})

    # 8. 团队-地点位于 (15条)
    all_teams = [t for sublist in TEAMS.values() for t in sublist]
    for team in all_teams[:15]:
        edges.append({"from": team, "to": random.choice(LOCATIONS), "relation": "位于"})

    return edges

# 执行生成
employees = generate_employees(50)
policies = generate_policies(25)
edges = generate_edges(employees, policies)

# 保存数据
with open("employees.json", "w", encoding="utf-8") as f:
    json.dump(employees, f, ensure_ascii=False, indent=2)
with open("policies.json", "w", encoding="utf-8") as f:
    json.dump(policies, f, ensure_ascii=False, indent=2)
with open("edges.json", "w", encoding="utf-8") as f:
    json.dump(edges, f, ensure_ascii=False, indent=2)

print(f"成功生成 {len(employees)} 个员工, {len(policies)} 个制度, {len(edges)} 条关系边。")
