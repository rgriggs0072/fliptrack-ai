"""
FlipTrack AI - Home Page
========================
AI-first property investment tracking for house flippers and rental rehab companies.
"""

import streamlit as st
import pandas as pd
import anthropic
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.snowflake_connection import get_connection
from utils.auth import check_authentication

# Page config
st.set_page_config(
    page_title="FlipTrack AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Check authentication
if not check_authentication():
    st.stop()

# Get user info from session
user_info = st.session_state.get('user_info', {})
client_name = user_info.get('client_name', 'Guest')

# Header
st.markdown('<h1 class="main-header">🏠 FlipTrack AI</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="subtitle">Welcome back, {client_name}!</p>', unsafe_allow_html=True)

st.divider()

# Quick Stats
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Active Projects",
        value="1",
        delta="+0 this month"
    )

with col2:
    st.metric(
        label="Total Invested",
        value="$146.5K",
        delta="+$0 this month"
    )

with col3:
    st.metric(
        label="CI / MI Split",
        value="90% / 10%",
        delta="Cash heavy"
    )

with col4:
    st.metric(
        label="Days Active",
        value="1,237",
        delta="41 months"
    )

st.divider()

# AI Command Center
st.subheader("🤖 AI Command Center")
st.markdown("*Ask me anything about your projects or tell me what to do...*")

# Command input
user_command = st.text_input(
    "What would you like to know or do?",
    placeholder="e.g., 'How much spent on lumber?', 'Show dashboard', 'Who is my most expensive vendor?'",
    label_visibility="collapsed"
)

# Example commands
with st.expander("💡 Example Commands & Questions"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Navigation:**
        - "Show my dashboard"
        - "Add an expense"
        - "Generate report"
        - "Import spreadsheet"
        """)
    with col2:
        st.markdown("""
        **Ask Questions:**
        - "How much spent on lumber?"
        - "Total plumbing costs?"
        - "Who's my top vendor?"
        - "What's my CI/M ratio?"
        """)

# Process command with AI
if user_command:
    with st.spinner("🤖 Processing your request..."):
        
        claude = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
        
        # First, determine if it's a navigation command or a data query
        classification_prompt = f"""
        User said: "{user_command}"
        
        Is this a NAVIGATION request (go to a page) or a DATA_QUERY (asking about their data)?
        
        NAVIGATION examples: "show dashboard", "add expense", "generate report", "import data"
        DATA_QUERY examples: "how much spent on lumber?", "who is my top vendor?", "total plumbing costs?"
        
        Respond with ONLY: NAVIGATION or DATA_QUERY
        """
        
        try:
            classification = claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=20,
                messages=[{"role": "user", "content": classification_prompt}]
            )
            
            intent = classification.content[0].text.strip()
            
            # NAVIGATION - Route to pages
            if "NAVIGATION" in intent:
                action_prompt = f"""
                User said: "{user_command}"
                
                Which page do they want?
                - ADD_EXPENSE: add, record, enter expense/payment
                - DASHBOARD: view dashboard, see data, metrics
                - EXPORT: generate report, export, Excel
                - IMPORT: import, upload spreadsheet
                
                Respond with ONLY the action code.
                """
                
                response = claude.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=50,
                    messages=[{"role": "user", "content": action_prompt}]
                )
                
                action = response.content[0].text.strip()
                
                if "ADD_EXPENSE" in action:
                    st.success("✅ Taking you to add an expense...")
                    st.switch_page("pages/2_➕_Add_Expense.py")
                elif "DASHBOARD" in action:
                    st.success("✅ Opening your dashboard...")
                    st.switch_page("pages/1_📊_Dashboard.py")
                elif "EXPORT" in action:
                    st.success("✅ Opening report generator...")
                    st.switch_page("pages/4_📄_Export_Report.py")
                elif "IMPORT" in action:
                    st.success("✅ Opening data import...")
                    st.switch_page("pages/3_📥_Import_Data.py")
            
            # DATA_QUERY - Answer with SQL
            elif "DATA_QUERY" in intent:
                from utils.snowflake_connection import get_connection, get_client_database
                
                conn = get_connection()
                database, schema = get_client_database()
                cursor = conn.cursor()
                
                # Get user's project info
                cursor.execute(f"USE DATABASE {database}")
                cursor.execute(f"USE SCHEMA {schema}")
                
                cursor.execute("SELECT project_id, project_name FROM PROJECTS LIMIT 1")
                project = cursor.fetchone()
                project_id = project[0] if project else None
                
                if not project_id:
                    st.error("No projects found!")
                else:
                    # Have AI generate SQL
                    sql_prompt = f"""
                    User question: "{user_command}"
                    
                    Database schema:
                    - PROJECTS: project_id, project_name, address, project_type, purchase_price, total_spent_ci, total_spent_mi
                    - EXPENSES: expense_id, project_id, expense_date, amount, investment_type (CI/MI), vendor_name, description, category
                    - Categories: Acquisition, Closing Costs, Demo, Cleanup, Concrete, Framing, Plumbing, Electrical, HVAC, Roofing, Drywall, Painting, Flooring, Materials, Utilities, etc.
                    
                    Current project_id: '{project_id}'
                    
                    Generate a SQL query to answer the user's question. The query should:
                    - Filter by project_id = '{project_id}' when querying EXPENSES
                    - Use proper aggregation (SUM, COUNT, AVG, etc.)
                    - Return relevant columns for display
                    - Be safe (read-only SELECT queries)
                    
                    Respond with ONLY the SQL query, no explanations or markdown.
                    """
                    
                    sql_response = claude.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": sql_prompt}]
                    )
                    
                    sql_query = sql_response.content[0].text.strip()
                    
                    # Clean up SQL (remove markdown if present)
                    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
                    
                    # Execute the query
                    try:
                        cursor.execute(sql_query)
                        results = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        
                        if results:
                            # Show results
                            st.success("✅ Here's what I found:")
                            
                            # If single value, show as metric
                            if len(results) == 1 and len(columns) == 1:
                                value = results[0][0]
                                if isinstance(value, (int, float)):
                                    st.metric(label="Result", value=f"${value:,.2f}" if value > 100 else f"{value:,.2f}")
                                else:
                                    st.info(f"**{value}**")
                            
                            # If table, show as dataframe
                            else:
                                df = pd.DataFrame(results, columns=columns)
                                st.dataframe(df, use_container_width=True, hide_index=True)
                            
                            # Show the SQL query in expander
                            with st.expander("🔍 SQL Query Used"):
                                st.code(sql_query, language="sql")
                        
                        else:
                            st.info("No results found for your query.")
                    
                    except Exception as e:
                        st.error(f"Query error: {e}")
                        with st.expander("🐛 Debug Info"):
                            st.code(sql_query, language="sql")
                
                cursor.close()
        
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# Recent Activity
st.subheader("📊 Your Projects")

# Mock data - will be replaced with real Snowflake query
project_data = {
    "Project": ["5122 Bonnell Ave"],
    "Type": ["Rental Rehab"],
    "Status": ["In Progress"],
    "Purchase": ["$86,271"],
    "Invested": ["$146,546"],
    "Days": [1237],
    "Budget %": ["N/A"]
}

import pandas as pd
df = pd.DataFrame(project_data)

st.dataframe(df, use_container_width=True, hide_index=True)

# Info boxes
st.divider()

info_col1, info_col2 = st.columns(2)

with info_col1:
    st.info("""
    **🎯 Getting Started**
    
    1. **Add your first expense** - Use voice, receipt scan, or manual entry
    2. **Import existing data** - Upload your Excel spreadsheet
    3. **Set budgets** - Track spending vs. budget
    4. **Generate reports** - Export for investors/lenders
    """)

with info_col2:
    st.success("""
    **✨ AI Features**
    
    - 🎤 **Voice Entry** - Just speak your expenses
    - 📸 **Receipt OCR** - Snap a photo, auto-extract data
    - 🤖 **Smart Categories** - AI categorizes automatically
    - 💡 **Budget Alerts** - Get notified when over budget
    """)

# Footer
st.divider()
st.caption("FlipTrack AI - Powered by Claude & Snowflake | © 2026")