"""
Utility functions for frontend.

Helper functions for API calls, styling, and state management.
"""

import streamlit as st
import requests
from typing import Optional, Dict
import json
import os
from datetime import datetime


def get_api_endpoint() -> str:
    """
    Get backend API endpoint.
    
    Returns:
        API base URL
    """
    # Try to get from environment, then secrets, then default
    if "api_endpoint" in st.secrets:
        return st.secrets["api_endpoint"]
    return os.getenv("API_ENDPOINT", "http://localhost:8000/api/v1")


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    timeout: int = 30,
    headers: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Make HTTP request to backend API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (without base URL)
        data: Request data
        timeout: Request timeout in seconds
        headers: Optional additional headers
    
    Returns:
        Response JSON or None on error
    """
    try:
        api_endpoint = get_api_endpoint()
        url = f"{api_endpoint}{endpoint}" if endpoint.startswith("/") else f"{api_endpoint}/{endpoint}"
        
        # Add auth header if available
        request_headers = headers or {}
        auth_header = get_auth_header()
        request_headers.update(auth_header)
        
        if method.upper() == "GET":
            response = requests.get(url, headers=request_headers, timeout=timeout)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=request_headers, timeout=timeout)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=request_headers, timeout=timeout)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=request_headers, timeout=timeout)
        else:
            st.error(f"Unsupported HTTP method: {method}")
            return None
        
        if response.status_code >= 200 and response.status_code < 300:
            return response.json() if response.text else None
        else:
            error_detail = response.json().get("detail", "Unknown error") if response.text else "Unknown error"
            st.error(f"Request failed ({response.status_code}): {error_detail}")
            return None
    
    except requests.exceptions.Timeout:
        st.error("Request timeout. The server is taking too long to respond.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Connection error. Cannot reach the backend server.")
        return None
    except Exception as e:
        st.error(f"Request error: {str(e)}")
        return None


def init_session_state():
    """Initialize Streamlit session state."""
    # Initialize auth tokens
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    
    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None
    
    # Initialize user info
    if "username" not in st.session_state:
        st.session_state.username = None
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    # Initialize history
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    
    # Initialize session ID
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())


def save_user_info(username: str, user_id: str):
    """
    Save user information to session state.
    
    Args:
        username: Username
        user_id: User ID
    """
    st.session_state.username = username
    st.session_state.user_id = user_id


def save_token(access_token: str, refresh_token: Optional[str] = None):
    """
    Save tokens to session state.
    
    Args:
        access_token: JWT access token
        refresh_token: Optional refresh token
    """
    st.session_state.access_token = access_token
    if refresh_token:
        st.session_state.refresh_token = refresh_token


def get_auth_header() -> Dict[str, str]:
    """
    Get authorization header.
    
    Returns:
        Authorization header dict, empty if not authenticated
    """
    if "access_token" in st.session_state and st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


def is_authenticated() -> bool:
    """
    Check if user is authenticated.
    
    Returns:
        True if access token exists, False otherwise
    """
    return "access_token" in st.session_state and st.session_state.access_token is not None


def apply_custom_css():
    """Apply custom CSS styling to Streamlit app."""
    custom_css = """
    <style>
    /* Header styling */
    .main h1, .main h2, .main h3 {
        color: #1f77b4;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 5px;
        font-weight: 600;
    }
    
    /* Metric styling */
    .stMetric {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1f77b4;
    }
    
    /* Code block styling */
    .stCodeBlock {
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def format_timestamp(timestamp: str) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: ISO format timestamp or datetime string
    
    Returns:
        Human-readable timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def render_kg_graph(kg_paths: list):
    """
    Render knowledge graph paths visualization.
    
    Args:
        kg_paths: List of knowledge graph paths
    """
    if not kg_paths:
        st.info("No knowledge graph paths found.")
        return
    
    # Simple text-based KG visualization
    for idx, path in enumerate(kg_paths, 1):
        st.subheader(f"KG Path {idx}")
        
        if isinstance(path, dict):
            # Display triples
            if "triples" in path:
                for triple in path["triples"]:
                    st.write(f"**{triple[0]}** → {triple[1]} → **{triple[2]}**")
            
            # Display metadata
            if "confidence" in path:
                st.write(f"Confidence: {path['confidence']:.2%}")
            
            if "provenance" in path:
                st.write(f"Source: {path['provenance']}")
        else:
            st.write(str(path))


def render_settings_page():
    """Render settings page UI."""
    st.header("⚙️ Settings")
    st.markdown("---")
    
    # API Configuration
    st.subheader("🔗 API Configuration")
    
    api_endpoint = st.text_input(
        "API Endpoint",
        value=get_api_endpoint(),
        help="Backend API base URL"
    )
    
    if st.button("Update API Endpoint"):
        os.environ["API_ENDPOINT"] = api_endpoint
        st.success("API endpoint updated!")
    
    st.markdown("---")
    
    # Session Information
    st.subheader("👤 Session Information")
    
    if is_authenticated():
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Username:** {st.session_state.get('username', 'N/A')}")
        
        with col2:
            st.write(f"**User ID:** {st.session_state.get('user_id', 'N/A')}")
        
        st.write(f"**Session ID:** {st.session_state.get('session_id', 'N/A')}")
    else:
        st.info("Not authenticated. Please login first.")
    
    st.markdown("---")
    
    # Display Preferences
    st.subheader("🎨 Display Preferences")
    
    results_per_page = st.slider(
        "Results per page",
        1,
        20,
        5,
        help="Number of results to display per page"
    )
    
    auto_refresh = st.checkbox(
        "Auto-refresh history",
        value=True,
        help="Automatically refresh query history"
    )
    
    st.markdown("---")
    
    # About
    st.subheader("ℹ️ About")
    
    st.write("""
    **RAG Dynamic Router v1.0.0**
    
    A sophisticated retrieval-augmented generation system that dynamically routes queries
    to optimal information sources using vector search, knowledge graphs, and intelligent
    ranking algorithms.
    
    **Features:**
    - Dynamic routing based on query characteristics
    - Multi-source evidence integration
    - Knowledge graph support
    - Session history tracking
    - Real-time performance metrics
    """)


# ==================== 翻译函数 ====================
def t(key: str):
    """
    翻译函数，根据语言返回对应文本
    
    Args:
        key: 翻译键名
        
    Returns:
        对应语言的文本
    """
    import streamlit as st
    
    translations = {
        "zh": {
            # 导航菜单
            "Query": "查询",
            "History": "历史记录",
            "KG Visualization": "知识图谱",
            "Metrics": "系统指标",
            "Settings": "设置",
            "Logout": "退出登录",
            # 页面标题
            "Query RAG System": "RAG智能问答系统",
            "Query History": "查询历史",
            "Knowledge Graph Visualization": "知识图谱可视化",
            "System Metrics": "系统指标",
            # 通用
            "No queries in history yet": "暂无查询记录",
            "Total Queries": "总查询数",
            "Success": "成功",
            "Failed": "失败",
            "Details": "详情",
            "Export as JSON": "导出JSON",
            "Clear History": "清除历史",
            "Version 1.0.0": "版本 1.0.0",
            "Navigation": "导航",
            "User": "用户",
            "Ask a question:": "请输入您的问题：",
            "Top K Results": "返回结果数",
            "Strategy Hint": "路由策略",
            "AUTO": "自动",
            "🚀 Submit Query": "🚀 提交查询",
            "🗑️ Clear": "🗑️ 清除",
            "📝 Recent Queries": "📝 最近查询",
            "💡 Answer": "💡 答案",
            "📚 Evidence Sources": "📚 证据来源",
            "Routing Decision": "路由决策",
            "Performance Metrics": "性能指标",
            "Login to RAG System": "登录RAG系统",
            "Username": "用户名",
            "Password": "密码",
            "Login": "登录",
            "Logout": "退出",
            "Submit Query": "提交查询",
            "Clear": "清除",
            "Answer": "答案",
            "Evidence Sources": "证据来源",
            "RAG Dynamic Router": "RAG动态路由器",
            "Sign In": "登录",
            "Sign Out": "退出",
            "Settings": "设置",
            "Display Preferences": "显示偏好",
            "Results per page": "每页结果数",
            "Auto-refresh history": "自动刷新历史",
            "About": "关于",
            "Version": "版本",
            "Sign In to RAG System": "登录 RAG 智能问答系统",
            "Enter username": "请输入用户名",
            "Enter password": "请输入密码",
            "Login failed": "登录失败",
            "Connection error": "连接错误",
            "Please enter both username and password": "请输入用户名和密码",
            "Login successful! Redirecting...": "登录成功！正在跳转...",
            "Not authenticated. Please login first.": "未登录，请先登录",
            "Query": "查询",
        },
        "en": {
            # English - 原版英文
        }
    }
    
    # 获取当前语言，默认为英文
    lang = st.session_state.get("language", "en")
    return translations.get(lang, translations["en"]).get(key, key)


def get_current_language() -> str:
    """获取当前语言设置"""
    import streamlit as st
    return st.session_state.get("language", "en")
