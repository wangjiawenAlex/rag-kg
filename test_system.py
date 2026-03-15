#!/usr/bin/env python3
"""
RAG Dynamic Router - Quick Test Script
快速验证系统功能的测试脚本
"""

import requests
import json
import time
import sys
from typing import Optional, Dict

# 配置
BASE_URL = "http://localhost:8000/api/v1"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"

class Colors:
    """颜色输出"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def test_health_check() -> bool:
    """测试系统健康检查"""
    print_info("正在测试系统健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/admin/health", timeout=5)
        if response.status_code == 200:
            print_success("系统健康检查通过")
            return True
        else:
            print_error(f"健康检查失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"无法连接到 {BASE_URL}")
        print_warning("请确保后端服务正在运行: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"健康检查出错: {str(e)}")
        return False

def test_login() -> Optional[str]:
    """测试登录功能"""
    print_info("正在测试登录功能...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={
                "username": DEMO_USERNAME,
                "password": DEMO_PASSWORD
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_success(f"登录成功，获得访问令牌")
                print(f"  令牌长度: {len(token)} 字符")
                return token
            else:
                print_error("响应中未找到 access_token")
                return None
        else:
            print_error(f"登录失败: {response.status_code}")
            print(f"  响应: {response.json()}")
            return None
    except Exception as e:
        print_error(f"登录异常: {str(e)}")
        return None

def test_query(token: str) -> bool:
    """测试查询功能"""
    print_info("正在测试查询功能...")
    
    test_query_text = "产品 X 的主要特性是什么？"
    
    try:
        response = requests.post(
            f"{BASE_URL}/query",
            json={
                "query": test_query_text,
                "session_id": "test-session-001",
                "top_k": 3,
                "router_hint": None
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("查询成功")
            
            # 验证响应结构
            required_fields = ["answer", "evidence", "router_decision", "latency_ms"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print_warning(f"响应缺少字段: {missing_fields}")
            else:
                print_success("响应包含所有必需字段")
            
            # 显示关键信息
            print(f"  答案: {data.get('answer', 'N/A')[:100]}...")
            print(f"  证据数: {len(data.get('evidence', []))}")
            print(f"  路由策略: {data.get('router_decision', {}).get('strategy', 'N/A')}")
            print(f"  延迟: {data.get('latency_ms', 'N/A')}ms")
            
            return True
        else:
            print_error(f"查询失败: {response.status_code}")
            print(f"  响应: {response.json() if response.text else 'Empty'}")
            return False
    except requests.exceptions.Timeout:
        print_error("查询超时（>10秒）")
        return False
    except Exception as e:
        print_error(f"查询异常: {str(e)}")
        return False

def test_ingest_documents(token: str) -> bool:
    """测试文档摄入功能"""
    print_info("正在测试文档摄入功能...")
    
    test_doc = {
        "document_id": "test-doc-001",
        "title": "测试文档",
        "content": "这是一个测试文档。它包含关于产品 X 的信息。产品 X 具有以下特性: 高性能、易使用、低成本。",
        "metadata": {
            "source": "test",
            "type": "manual"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/documents",
            json={"documents": [test_doc]},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("文档摄入成功")
            print(f"  总文档数: {data.get('total_documents', 'N/A')}")
            print(f"  文本块数: {data.get('total_chunks', 'N/A')}")
            print(f"  成功: {data.get('successful', 'N/A')}")
            print(f"  失败: {data.get('failed', 'N/A')}")
            return True
        else:
            print_error(f"文档摄入失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"文档摄入异常: {str(e)}")
        return False

def test_admin_metrics(token: str) -> bool:
    """测试管理指标功能"""
    print_info("正在测试管理指标功能...")
    
    try:
        # 获取路由策略
        response = requests.get(
            f"{BASE_URL}/admin/route-strategies",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            strategies = data.get("strategies", [])
            print_success(f"获得 {len(strategies)} 个路由策略")
            
            for strategy in strategies:
                print(f"  - {strategy.get('name', 'N/A')}: {strategy.get('description', '')[:50]}...")
            
            return True
        else:
            print_error(f"获取策略失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"管理指标异常: {str(e)}")
        return False

def test_refresh_token(token: str) -> Optional[str]:
    """测试令牌刷新功能"""
    print_info("正在测试令牌刷新功能...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/refresh",
            json={"refresh_token": token},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            new_token = data.get("access_token")
            if new_token:
                print_success("令牌刷新成功")
                return new_token
            else:
                print_warning("刷新响应中未找到新令牌")
                return None
        else:
            print_warning(f"令牌刷新返回: {response.status_code}")
            return None
    except Exception as e:
        print_warning(f"令牌刷新异常: {str(e)}")
        return None

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("RAG Dynamic Router - 系统功能测试")
    print("="*60 + "\n")
    
    results = {
        "健康检查": False,
        "用户登录": False,
        "查询功能": False,
        "文档摄入": False,
        "管理指标": False,
        "令牌刷新": False
    }
    
    # 1. 健康检查
    if not test_health_check():
        print_error("系统不可用，停止测试")
        return results
    results["健康检查"] = True
    print()
    
    # 2. 登录
    token = test_login()
    if not token:
        print_error("无法获得认证令牌，停止测试")
        return results
    results["用户登录"] = True
    print()
    
    # 3. 查询
    results["查询功能"] = test_query(token)
    print()
    
    # 4. 文档摄入
    results["文档摄入"] = test_ingest_documents(token)
    print()
    
    # 5. 管理指标
    results["管理指标"] = test_admin_metrics(token)
    print()
    
    # 6. 令牌刷新
    new_token = test_refresh_token(token)
    results["令牌刷新"] = new_token is not None
    print()
    
    # 总结
    print("="*60)
    print("测试结果总结")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}通过{Colors.END}" if result else f"{Colors.RED}失败{Colors.END}"
        print(f"{test_name:<15} {status}")
    
    print("-"*60)
    print(f"总体: {passed}/{total} 测试通过")
    
    if passed == total:
        print_success("所有测试通过！系统正常运行。")
    elif passed >= total * 0.7:
        print_warning(f"部分测试失败（{total - passed}/{total}）")
    else:
        print_error(f"大多数测试失败（仅 {passed}/{total} 通过）")
    
    print("="*60 + "\n")
    
    return results

if __name__ == "__main__":
    print_info("开始 RAG Dynamic Router 系统测试...")
    print_info(f"目标URL: {BASE_URL}\n")
    
    results = run_all_tests()
    
    # 返回退出码
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    sys.exit(0 if passed == total else 1)
