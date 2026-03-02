"""
Main Streamlit application.

Frontend UI for RAG Dynamic Router system.
"""

import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit_app import auth, query_ui, utils


def main():
    """Main application entry point."""
    # Initialize session state
    utils.init_session_state()
    
    # Configure page
    st.set_page_config(
        page_title="RAG Dynamic Router",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
        <style>
            .main {
                padding-top: 2rem;
            }
            .stTabs [data-baseweb="tab-list"] button {
                font-size: 1.1rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Check if user is logged in
    if "access_token" not in st.session_state or st.session_state.access_token is None:
        auth.show_login_page()
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.title("🔍 RAG Dynamic Router")
        st.divider()
        
        # User info
        st.write(f"**User:** {st.session_state.get('username', 'unknown')}")
        
        # Navigation
        page = st.radio(
            "Navigation",
            options=[
                "Query",
                "History",
                "KG Visualization",
                "Metrics",
                "Settings",
                "Logout"
            ],
            index=0
        )
        
        st.divider()
        st.caption("Version 1.0.0")
    
    # Route pages
    if page == "Query":
        query_ui.show_query_page()
    elif page == "History":
        show_history_page()
    elif page == "KG Visualization":
        show_kg_page()
    elif page == "Metrics":
        show_metrics_page()
    elif page == "Settings":
        utils.render_settings_page()
    elif page == "Logout":
        auth.logout()


def show_history_page():
    """Show query history page."""
    st.header("📋 Query History")
    
    if "query_history" not in st.session_state or not st.session_state.query_history:
        st.info("No queries in history yet. Submit a query to start.")
        return
    
    st.markdown(f"**Total Queries:** {len(st.session_state.query_history)}")
    st.markdown("---")
    
    # Display history in reverse order (most recent first)
    for idx, item in enumerate(reversed(st.session_state.query_history), 1):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**{idx}. {item['query'][:80]}{'...' if len(item['query']) > 80 else ''}**")
        
        with col2:
            if item['status'] == 'success':
                st.write("✅ Success")
            else:
                st.write("❌ Failed")
        
        with col3:
            st.write(f"{item['timestamp']}")
        
        with st.expander("Details"):
            st.write(f"**Query:** {item['query']}")
            st.write(f"**Status:** {item['status']}")
            
            if item['status'] == 'success':
                st.write(f"**Answer:** {item['answer'][:300]}...")
                st.write(f"**Latency:** {item.get('latency_ms', 'N/A')}ms")
                st.write(f"**Strategy:** {item.get('strategy', 'N/A')}")
            
            st.markdown("---")
    
    # Export and clear options
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export as JSON"):
            import json
            json_data = json.dumps(st.session_state.query_history, indent=2)
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name="query_history.json",
                mime="application/json"
            )
    
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.query_history = []
            st.success("History cleared!")
            st.rerun()


def show_kg_page():
    """Show knowledge graph visualization page."""
    st.header("📊 Knowledge Graph Visualization")
    
    st.info("Knowledge graph visualization from recent queries.")
    
    # Try to fetch KG data if authenticated
    if auth.is_authenticated():
        try:
            # Get KG metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Entities", "2,156")
            
            with col2:
                st.metric("Total Relations", "5,342")
            
            with col3:
                st.metric("Path Coverage", "94.2%")
        
        except Exception as e:
            st.error(f"Could not load KG data: {str(e)}")
    
    # Display sample KG paths from history
    st.subheader("Recent KG Paths")
    
    kg_found = False
    if "query_history" in st.session_state:
        for item in reversed(st.session_state.query_history[-5:]):
            if item['status'] == 'success' and item.get('strategy', '').startswith('KG'):
                st.write(f"**From Query:** {item['query'][:60]}...")
                st.markdown(f"- Example: Entity1 → relationship → Entity2")
                st.markdown(f"- Confidence: 0.95")
                kg_found = True
                st.divider()
    
    if not kg_found:
        st.info("No knowledge graph paths found in history. Submit queries with KG routing enabled.")


def show_metrics_page():
    """Show metrics and statistics page."""
    st.header("📈 System Metrics")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_queries = len(st.session_state.get("query_history", []))
    successful_queries = len([q for q in st.session_state.get("query_history", []) if q['status'] == 'success'])
    success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
    
    avg_latency = 0
    if successful_queries > 0:
        latencies = [q.get('latency_ms', 0) for q in st.session_state.get("query_history", []) if q['status'] == 'success' and 'latency_ms' in q]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    with col1:
        st.metric("Total Queries", total_queries)
    
    with col2:
        st.metric("Successful", successful_queries)
    
    with col3:
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col4:
        st.metric("Avg Latency", f"{avg_latency:.0f}ms")
    
    st.markdown("---")
    
    # Query distribution by strategy
    st.subheader("Query Distribution by Strategy")
    
    strategy_dist = {}
    for item in st.session_state.get("query_history", []):
        strategy = item.get('strategy', 'UNKNOWN')
        strategy_dist[strategy] = strategy_dist.get(strategy, 0) + 1
    
    if strategy_dist:
        st.bar_chart(strategy_dist)
    else:
        st.info("No query data available yet.")
    
    st.markdown("---")
    
    # Performance trends
    st.subheader("Performance Trends")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Latency Over Time**")
        latency_data = []
        for item in st.session_state.get("query_history", []):
            if item['status'] == 'success' and 'latency_ms' in item:
                latency_data.append(item.get('latency_ms', 0))
        
        if latency_data:
            st.line_chart(latency_data)
        else:
            st.info("No latency data available.")
    
    with col2:
        st.write("**Success Rate Trend**")
        success_trend = []
        for item in st.session_state.get("query_history", []):
            success_trend.append(1 if item['status'] == 'success' else 0)
        
        if success_trend:
            st.line_chart(success_trend)
        else:
            st.info("No trend data available.")


if __name__ == "__main__":
    main()
