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
from utils.branding import get_brand, apply_custom_css, display_logo

# Load brand
brand = get_brand("kituwah_properties")

# Page config
st.set_page_config(
    page_title=f"{brand['company']} - FlipTrack AI",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom branding CSS
apply_custom_css(brand)

# Check authentication
if not check_authentication():
    st.stop()

# Get user info from session
user_info = st.session_state.get('user_info', {})
client_name = user_info.get('client_name', 'Guest')

# Header with logo
col1, col2 = st.columns([1, 3])
with col1:
    display_logo(brand, size="small")
with col2:
    st.markdown(f'<h1 class="main-header">{brand["company"]}</h1>', unsafe_allow_html=True)
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
                - DASHBOARD: view dashboard, see data, metrics, analytics
                - EXPORT: generate report, export, summary report, investor report
                - IMPORT: import, upload spreadsheet, upload data
                
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
            
            # DATA_QUERY - Route to AI Data Intelligence
            elif "DATA_QUERY" in intent:
                st.success("🧠 Opening AI Data Intelligence to answer your question...")
                # Store the question in session state so AI Data Intelligence can use it
                st.session_state.pending_question = user_command
                st.switch_page("pages/5_🧠_AI_Data_Intelligence.py")
        
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

st.dataframe(df, width="stretch", hide_index=True)

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
st.caption("FlipTrack AI - Powered by Claude & Chainlink Analytics LLC. | © 2026")
