"""
FlipTrack AI - AI Data Intelligence
===================================
Ask anything about your data and get instant insights with export capabilities.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from utils.snowflake_connection import get_connection, get_client_database
from agents.query_agent import QueryAgent
from utils.branding import get_brand, apply_custom_css

# Load brand
brand = get_brand("kituwah_properties")

# Page config
st.set_page_config(
    page_title=f"AI Data Intelligence - {brand['company']}",
    page_icon="🧠",
    layout="wide"
)

# Apply branding
apply_custom_css(brand)

# Check authentication
if not check_authentication():
    st.stop()

# Header
st.title("🧠 AI Data Intelligence")
st.markdown("**Ask anything about your projects - get instant answers with intelligent insights**")

st.divider()

# Get connection
conn = get_connection()
database, schema = get_client_database()

cursor = conn.cursor()
cursor.execute(f"USE DATABASE {database}")
cursor.execute(f"USE SCHEMA {schema}")

# Get projects for context
cursor.execute("SELECT project_id, project_name FROM PROJECTS")
projects = cursor.fetchall()

if not projects:
    st.warning("No projects found!")
    st.stop()

# Initialize query agent
agent = QueryAgent()

# Initialize session state for query history
if 'query_history' not in st.session_state:
    st.session_state.query_history = []

# Main query interface
col1, col2 = st.columns([3, 1])

with col1:
    # Check if there's a pending question from Home page
    default_question = st.session_state.pop('pending_question', '')
    
    user_question = st.text_area(
        "What would you like to know?",
        value=default_question,
        placeholder="e.g., 'How much have I spent on lumber in the last 6 months?'",
        height=100,
        help="Ask any question about your expenses, vendors, categories, or projects"
    )

with col2:
    st.markdown("### 🎯 Quick Questions")
    if st.button("💰 Top vendors", width="stretch"):
        user_question = "Who are my top 10 vendors by total spending?"
    if st.button("📊 Spending by category", width="stretch"):
        user_question = "Show spending breakdown by category"
    if st.button("📅 Last 30 days", width="stretch"):
        user_question = "What did I spend in the last 30 days?"
    if st.button("🏗️ By project", width="stretch"):
        user_question = "Show total spending for each project"

# Project filter
st.markdown("### 🎯 Scope")
scope_option = st.radio(
    "Query scope:",
    ["All Projects", "Current Project Only"],
    horizontal=True,
    help="Choose whether to query across all projects or just one"
)

project_id = None if scope_option == "All Projects" else projects[0][0]

# Execute query button
if st.button("🚀 Run Query", type="primary", disabled=not user_question):
    
    with st.spinner("🤖 AI is analyzing your question and generating SQL..."):
        
        # Generate smart SQL
        result = agent.generate_smart_sql(
            user_question=user_question,
            project_id=project_id,
            database=database,
            schema=schema
        )
        
        if result:
            sql_query = result['sql']
            explanation = result.get('explanation', '')
            
            # Show explanation
            if explanation:
                st.info(f"💡 {explanation}")
            
            # Execute query
            try:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                if results:
                    # Convert to dataframe
                    df = pd.DataFrame(results, columns=columns)
                    
                    # Convert Snowflake DECIMAL to float for proper display
                    for col in df.columns:
                        if df[col].dtype == 'object':
                            try:
                                # Try to convert to numeric (handles Decimal objects)
                                df[col] = pd.to_numeric(df[col], errors='ignore')
                            except:
                                pass
                    
                    # Store in session state for export
                    st.session_state.last_query_df = df
                    st.session_state.last_query_sql = sql_query
                    st.session_state.last_query_question = user_question
                    
                    # Add to history
                    st.session_state.query_history.insert(0, {
                        'timestamp': datetime.now(),
                        'question': user_question,
                        'rows': len(df)
                    })
                    
                    # Keep only last 10 queries
                    st.session_state.query_history = st.session_state.query_history[:10]
                    
                    st.divider()
                    
                    # Results header with count
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.subheader(f"✅ Results ({len(df)} rows)")
                    
                    # Display results
                    st.dataframe(df, width="stretch", hide_index=True)
                    
                    # Export buttons
                    st.divider()
                    st.subheader("📥 Export Results")
                    
                    export_col1, export_col2, export_col3 = st.columns([1, 1, 2])
                    
                    with export_col1:
                        # Excel export
                        excel_data = agent.export_to_excel(df, sql_query, user_question)
                        st.download_button(
                            label="📊 Download Excel",
                            data=excel_data,
                            file_name=f"fliptrack_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch"
                        )
                    
                    with export_col2:
                        # PDF export
                        pdf_data = agent.export_to_pdf(df, sql_query, user_question)
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_data,
                            file_name=f"fliptrack_query_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            width="stretch"
                        )
                    
                    # Show SQL query
                    with st.expander("🔍 View SQL Query"):
                        st.code(sql_query, language="sql")
                
                else:
                    st.warning("No results found for your query.")
                    with st.expander("🔍 View SQL Query"):
                        st.code(sql_query, language="sql")
            
            except Exception as e:
                st.error(f"❌ Query error: {e}")
                with st.expander("🐛 Debug Info"):
                    st.code(sql_query, language="sql")
                    st.text(str(e))

# Query History Sidebar
st.divider()

if st.session_state.query_history:
    st.subheader("📜 Recent Queries")
    
    for idx, query in enumerate(st.session_state.query_history[:5]):
        with st.expander(f"🕐 {query['timestamp'].strftime('%H:%M:%S')} - {query['question'][:50]}..."):
            st.markdown(f"**Question:** {query['question']}")
            st.markdown(f"**Rows returned:** {query['rows']}")
            if st.button(f"Re-run this query", key=f"rerun_{idx}"):
                user_question = query['question']
                st.rerun()

# Tips
st.divider()

with st.expander("💡 Pro Tips"):
    st.markdown("""
    **Example Questions:**
    
    **Spending Analysis:**
    - "How much have I spent on concrete in the last year?"
    - "What are my total materials costs?"
    - "Show me all expenses over $1,000"
    
    **Vendor Analysis:**
    - "Who is my most expensive vendor?"
    - "How much have I paid Home Depot?"
    - "List all vendors I've used for plumbing"
    
    **Project Comparisons:**
    - "Compare spending across all my projects"
    - "Which project has the highest materials cost?"
    - "Show me CI vs MI breakdown by project"
    
    **Time-Based:**
    - "What did I spend last month?"
    - "Show expenses from Q4 2024"
    - "Total spending in 2024"
    
    **The AI will automatically:**
    - Include project names in results
    - Show breakdowns instead of just totals
    - Search across descriptions, vendors, and categories
    - Use proper date arithmetic
    """)

cursor.close()

# Footer
st.divider()
st.caption("FlipTrack AI - Ask anything, anytime")
