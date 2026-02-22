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
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.snowflake_connection import get_connection, get_client_database
from utils.auth import check_authentication
from utils.branding import get_brand, apply_custom_css
from utils.sidebar import render_sidebar          # ← NEW

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

# ── Sidebar (logo + nav — visible on every page) ──────────────────────────────
render_sidebar(brand)

# ── Header ────────────────────────────────────────────────────────────────────
user_info   = st.session_state.get("user_info", {})
client_name = user_info.get("client_name", "Guest")

st.markdown(f'<h1 class="main-header">{brand["company"]}</h1>', unsafe_allow_html=True)
st.markdown(f'<p class="subtitle">Welcome back, {client_name}!</p>', unsafe_allow_html=True)

st.divider()

# ── Quick Stats ───────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Active Projects",  "1",       delta="+0 this month")
with col2:
    st.metric("Total Invested",   "$146.5K", delta="+$0 this month")
with col3:
    st.metric("CI / MI Split",    "90% / 10%", delta="Cash heavy")
with col4:
    st.metric("Days Active",      "1,237",   delta="41 months")

st.divider()

# ── AI Vendor Intelligence ────────────────────────────────────────────────────
st.subheader("🤖 AI Vendor Intelligence")
st.markdown("*Autonomous business insights from your vendor data*")

from agents.vendor_intel_agent import VendorIntelligenceAgent

agent = VendorIntelligenceAgent()

try:
    conn   = get_connection()
    cursor = conn.cursor()

    database, schema = get_client_database()
    cursor.execute(f"USE DATABASE {database}")
    cursor.execute(f"USE SCHEMA {schema}")

    # One-time table setup (safe to call every run — uses IF NOT EXISTS)
    agent.ensure_tables(cursor)

    existing_insights = agent.get_latest_insights(cursor)

    if existing_insights:
        generated_time = existing_insights["generated_at"]
        time_ago = (datetime.now() - generated_time).total_seconds() / 3600

        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"Last analyzed: {int(time_ago)} hours ago")
        with col2:
            refresh = st.button("🔄 Refresh Insights", type="secondary")

        if refresh:
            with st.spinner("🤖 Agent is analyzing vendor data..."):
                insights = agent.analyze_vendors(cursor)
                if insights:
                    agent.save_insights(cursor, insights)
                    st.rerun()

        # ── Display insights ──────────────────────────────────────────────
        analysis = existing_insights["vendor_analysis"]

        if analysis and "top_vendors" in analysis:

            # Key insights strip
            key_insights = analysis.get("key_insights", [])
            if key_insights:
                st.markdown("### 💡 Key Findings")
                for insight in key_insights:
                    st.markdown(f"- {insight}")

            # Top vendors
            st.markdown("### 💼 Top Vendors")
            for vendor in analysis["top_vendors"][:3]:
                col1, col2, col3 = st.columns([2, 1, 3])
                with col1:
                    st.metric(vendor["vendor"], f"${vendor['spend']:,.0f}")
                with col2:
                    st.caption(f"{vendor['transactions']} transactions")
                with col3:
                    st.info(f"💡 {vendor['insight']}")

            # Savings opportunities
            st.markdown("### 💰 Savings Opportunities")
            total_savings = existing_insights["estimated_savings"]
            st.metric("Estimated Annual Savings", f"${total_savings:,.0f}")

            for opp in analysis.get("opportunities", [])[:4]:
                with st.expander(
                    f"💡 {opp['type'].replace('_', ' ').title()} — "
                    f"{opp.get('vendor_or_category', '')} "
                    f"(${opp['estimated_savings']:,.0f})"
                ):
                    st.markdown(f"**{opp['description']}**")
                    st.markdown(f"**Action:** {opp['action']}")

            # Recommendations
            st.markdown("### ✅ Recommendations")
            priority_colors = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            for rec in analysis.get("recommendations", [])[:4]:
                priority = rec.get("priority", "medium")
                effort   = rec.get("effort", "")
                with st.expander(
                    f"{priority_colors.get(priority, '⚪')} {rec['action'][:80]}…"
                ):
                    st.markdown(f"**Action:** {rec['action']}")
                    st.markdown(f"**Expected Impact:** {rec['expected_impact']}")
                    if effort:
                        st.caption(f"Effort: {effort}")

    else:
        st.info("No vendor analysis yet. Run your first analysis to get started.")
        if st.button("🚀 Run First Vendor Analysis", type="primary"):
            with st.spinner("🤖 Agent is analyzing your vendors… This may take 30 seconds…"):
                insights = agent.analyze_vendors(cursor)
                if insights:
                    agent.save_insights(cursor, insights)
                    st.success("✅ Analysis complete!")
                    st.rerun()

finally:
    cursor.close()

st.divider()

# ── Projects table ────────────────────────────────────────────────────────────
st.subheader("📊 Your Projects")

project_data = {
    "Project":   ["5122 Bonnell Ave"],
    "Type":      ["Rental Rehab"],
    "Status":    ["In Progress"],
    "Purchase":  ["$86,271"],
    "Invested":  ["$146,546"],
    "Days":      [1237],
    "Budget %":  ["N/A"],
}

st.dataframe(pd.DataFrame(project_data), use_container_width=True, hide_index=True)

st.divider()

info_col1, info_col2 = st.columns(2)

with info_col1:
    st.info("""
    **🎯 Getting Started**

    1. **Add your first expense** — voice, receipt scan, or manual entry
    2. **Import existing data** — upload your Excel spreadsheet
    3. **Set budgets** — track spending vs. budget
    4. **Generate reports** — export for investors/lenders
    """)

with info_col2:
    st.success("""
    **✨ AI Features**

    - 🎤 **Voice Entry** — just speak your expenses
    - 📸 **Receipt OCR** — snap a photo, auto-extract data
    - 🤖 **Smart Categories** — AI categorizes automatically
    - 💡 **Budget Alerts** — get notified when over budget
    """)

st.divider()
st.caption("FlipTrack AI — Powered by Claude & Snowflake | © 2026")
