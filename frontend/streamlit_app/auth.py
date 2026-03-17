"""
Authentication UI components.

Login and session management for Streamlit frontend.
"""

import streamlit as st
import requests
from typing import Optional
import json

# 导入翻译函数
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streamlit_app import utils


def show_login_page():
    """Display login page."""
    st.title(f"🤖 {utils.t('RAG Dynamic Router')}")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader(f"🔐 {utils.t('Sign In')}")
        
        username = st.text_input(utils.t("Username"), placeholder=utils.t("Enter username"), key="login_username")
        password = st.text_input(utils.t("Password"), type="password", placeholder=utils.t("Enter password"), key="login_password")
        
        if st.button(utils.t("Login"), use_container_width=True, type="primary"):
            login_user(username, password)
        
        st.markdown("---")
        st.info("**Demo Credentials:**\n\nUsername: `demo`\n\nPassword: `demo123`")
        
        st.markdown("---")
        st.caption(f"© 2025 RAG Router System {utils.t('Version 1.0.0')}")


def login_user(username: str, password: str):
    """
    Login user and store tokens.
    
    Args:
        username: Username
        password: Password
    """
    if not username or not password:
        st.error("Please enter both username and password")
        return
    
    try:
        from streamlit_app import utils
        
        api_endpoint = utils.get_api_endpoint()
        response = requests.post(
            f"{api_endpoint}/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data.get("access_token")
            st.session_state.refresh_token = data.get("refresh_token")
            st.session_state.username = username
            st.session_state.user_id = "user-001"  # Would be from token in production
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    
    except Exception as e:
        st.error(f"Connection error: {str(e)}")


def logout():
    """Logout user and clear session."""
    if "access_token" in st.session_state:
        del st.session_state.access_token
    if "refresh_token" in st.session_state:
        del st.session_state.refresh_token
    if "username" in st.session_state:
        del st.session_state.username
    if "user_id" in st.session_state:
        del st.session_state.user_id
    
    st.success("Logout successful!")
    st.rerun()


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return "access_token" in st.session_state and st.session_state.access_token is not None


def get_auth_header() -> dict:
    """Get authorization header with token."""
    if is_authenticated():
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}
