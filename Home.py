"""
FlipTrack AI - Home Page
========================
AI-first property investment tracking for house flippers and rental rehab companies.
"""

import streamlit as st
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

# Quick Actions
st.subheader("🚀 Quick Actions")

action_col1, action_col2, action_col3 = st.columns(3)

with action_col1:
    if st.button("🎤 Voice Entry", use_container_width=True, type="primary"):
        st.switch_page("pages/2_➕_Add_Expense.py")

with action_col2:
    if st.button("📸 Scan Receipt", use_container_width=True):
        st.switch_page("pages/2_➕_Add_Expense.py")

with action_col3:
    if st.button("📥 Import Excel", use_container_width=True):
        st.switch_page("pages/3_📥_Import_Data.py")

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
