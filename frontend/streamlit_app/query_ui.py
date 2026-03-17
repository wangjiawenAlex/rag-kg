"""
Query UI components.

Main query interface and result display.
"""

import streamlit as st
import requests
from typing import Dict, List, Optional
import json
from datetime import datetime

# 导入翻译函数
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from streamlit_app import utils


def show_query_page():
    """Display main query page."""
    st.header(f"🔍 {utils.t('Query RAG System')}")
    
    st.markdown("Submit a question and the system will retrieve relevant information using dynamic routing.")
    st.markdown("---")
    
    # Query settings
    col1, col2 = st.columns([3, 1])
    
    with col1:
        query = st.text_area(
            utils.t("Ask a question:"),
            placeholder="e.g., What are the key features of product X?",
            height=100,
            key="query_input"
        )
    
    with col2:
        st.subheader(utils.t("Settings"))
        top_k = st.slider(utils.t("Top K Results"), 1, 10, 5, key="top_k_slider")
        router_hint = st.selectbox(
            utils.t("Strategy Hint"),
            [utils.t("AUTO"), "VECTOR_ONLY", "KG_ONLY", "KG_THEN_VECTOR", "HYBRID_JOIN"],
            key="router_hint"
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        search_button = st.button(f"🚀 {utils.t('Submit Query')}", use_container_width=True, type="primary")
    
    with col2:
        clear_button = st.button(f"🗑️ {utils.t('Clear')}", use_container_width=True)
    
    # Handle actions
    if search_button:
        if query.strip():
            submit_query(query, top_k, router_hint if router_hint != utils.t("AUTO") else None)
        else:
            st.error("Please enter a question")
    
    if clear_button:
        st.session_state.query_input = ""
        st.rerun()
    
    # Display recent history
    if "query_history" in st.session_state and st.session_state.query_history:
        st.markdown("---")
        st.subheader(f"📝 {utils.t('Recent Queries')}")
        
        for idx, item in enumerate(reversed(st.session_state.query_history[-5:])):
            with st.expander(f"{item['query'][:60]}..." if len(item['query']) > 60 else item['query']):
                st.write(f"**Time:** {item['timestamp']}")
                st.write(f"**Status:** {item['status']}")
                if item['status'] == "success":
                    st.write(f"**{utils.t('Answer')}:** {item['answer'][:200]}...")
                    st.write(f"**Latency:** {item.get('latency_ms', 'N/A')}ms")
                    st.write(f"**Strategy:** {item.get('strategy', 'N/A')}")


def submit_query(query: str, top_k: int = 5, router_hint: Optional[str] = None) -> Optional[Dict]:
    """
    Submit query to backend.
    
    Args:
        query: Query text
        top_k: Number of top results
        router_hint: Optional routing strategy hint
    
    Returns:
        Query result or None on error
    """
    try:
        from streamlit_app import utils, auth
        
        if not auth.is_authenticated():
            st.error("Not authenticated. Please login first.")
            return None
        
        with st.spinner("Querying RAG system..."):
            api_endpoint = utils.get_api_endpoint()
            headers = auth.get_auth_header()
            
            payload = {
                "query": query,
                "session_id": st.session_state.get("user_id", "unknown"),
                "top_k": top_k,
                "router_hint": router_hint
            }
            
            response = requests.post(
                f"{api_endpoint}/query",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                display_results(result)
                
                # Store in history
                if "query_history" not in st.session_state:
                    st.session_state.query_history = []
                
                st.session_state.query_history.append({
                    "query": query,
                    "answer": result.get("answer", ""),
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success",
                    "latency_ms": result.get("latency_ms"),
                    "strategy": result.get("router_decision", {}).get("strategy", "UNKNOWN")
                })
                
                return result
            
            elif response.status_code == 401:
                st.error("Authentication failed. Please login again.")
            
            else:
                st.error(f"Query failed: {response.json().get('detail', 'Unknown error')}")
                
                if "query_history" not in st.session_state:
                    st.session_state.query_history = []
                
                st.session_state.query_history.append({
                    "query": query,
                    "answer": "",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "failed"
                })
        
        return None
    
    except requests.exceptions.Timeout:
        st.error("Request timeout. The server is taking too long to respond.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Connection error. Cannot reach the backend server.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def display_results(result: Dict):
    """
    Display query results.
    
    Args:
        result: Query response from backend
    """
    st.markdown("---")
    st.success("Query processed successfully!")
    st.markdown("---")
    
    # Main answer
    st.subheader("💡 Answer")
    st.write(result.get("answer", "No answer generated"))
    
    # Router decision
    st.markdown("---")
    router_decision = result.get("router_decision", {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Strategy",
            router_decision.get("strategy", "UNKNOWN")
        )
    
    with col2:
        st.metric(
            "Confidence",
            f"{router_decision.get('confidence', 0):.2%}"
        )
    
    with col3:
        st.metric(
            "Latency",
            f"{result.get('latency_ms', 0):.0f}ms"
        )
    
    # Routing reason
    if router_decision.get("reason"):
        with st.expander("📌 Routing Reason"):
            st.write(router_decision.get("reason"))
    
    # Evidence
    if result.get("evidence"):
        st.markdown("---")
        st.subheader(f"📚 {utils.t('Evidence Sources')}")
        
        for idx, evid in enumerate(result.get("evidence", []), 1):
            with st.expander(f"Source {idx}: {evid.get('title', 'Untitled')[:50]}"):
                st.write(f"**Type:** {evid.get('type', 'Unknown')}")
                st.write(f"**Confidence:** {evid.get('score', 0):.2%}")
                st.write(f"**Content:** {evid.get('content', '')[:500]}")
                if evid.get("metadata"):
                    st.write(f"**Metadata:** {json.dumps(evid.get('metadata'), indent=2)}")
    
    # Tabs for additional info
    tab1, tab2, tab3, tab4 = st.tabs([utils.t("Evidence Sources"), "Knowledge Graph", utils.t("Routing Decision"), utils.t("Performance Metrics")])
    
    with tab1:
        display_evidence(result.get("evidence", []))
    
    with tab2:
        display_kg_path(result.get("evidence", []))
    
    with tab3:
        display_router_decision(result.get("router_decision", {}))
    
    with tab4:
        display_metrics(result)


def display_evidence(evidence: List[Dict]):
    """
    Display evidence list.
    
    Args:
        evidence: List of evidence items
    """
    # TODO: Implement
    # 1. Create table with evidence items
    # 2. Show source, score, and text preview
    # 3. Allow sorting by score
    
    st.subheader("Evidence Sources")
    
    if evidence:
        # TODO: Display evidence table
        # Columns: Source, Score, Text Preview, Metadata
        pass
    else:
        st.info("No evidence found")


def display_kg_path(evidence: List[Dict]):
    """
    Display knowledge graph paths.
    
    Args:
        evidence: List of evidence items (filtered for KG items)
    """
    # TODO: Implement
    # 1. Filter evidence for KG sources
    # 2. Display as graph using pyvis or similar
    # 3. Show entity relationships
    
    st.subheader("Knowledge Graph Paths")
    
    kg_evidence = [e for e in evidence if e.get("source") == "kg"]
    
    if kg_evidence:
        # TODO: Render KG visualization
        pass
    else:
        st.info("No knowledge graph paths in results")


def display_router_decision(router_decision: Dict):
    """
    Display routing decision details.
    
    Args:
        router_decision: Router decision information
    """
    # TODO: Implement
    # 1. Show strategy name
    # 2. Show explanation/reason
    # 3. Show confidence score if available
    
    st.subheader(utils.t("Routing Decision"))
    
    if router_decision:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Strategy",
                router_decision.get("strategy", "Unknown")
            )
        
        with col2:
            st.metric(
                "Confidence",
                f"{router_decision.get('confidence', 0):.2%}"
            )
        
        with col3:
            st.metric(
                "Latency",
                f"{router_decision.get('latency_ms', 0)}ms"
            )
        
        st.info(f"**Reason:** {router_decision.get('reason', 'N/A')}")


def display_metrics(result: Dict):
    """
    Display query metrics.
    
    Args:
        result: Query response
    """
    # TODO: Implement
    # 1. Show latency breakdown
    # 2. Show number of retrievals
    # 3. Show score distribution
    
    st.subheader(utils.t("Performance Metrics"))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Latency", f"{result.get('latency_ms', 0)}ms")
    
    with col2:
        st.metric("Evidence Count", len(result.get("evidence", [])))
    
    with col3:
        st.metric("Top Score", f"{max([e.get('score', 0) for e in result.get('evidence', [])], default=0):.2%}")
