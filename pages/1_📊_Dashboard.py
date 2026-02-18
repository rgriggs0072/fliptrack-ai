"""
FlipTrack AI - Dashboard (Real Data)
====================================
Live dashboard showing actual project data from Snowflake.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from utils.snowflake_connection import get_connection, get_client_database

# Page config
st.set_page_config(
    page_title="Dashboard - FlipTrack AI",
    page_icon="📊",
    layout="wide"
)

# Check authentication
if not check_authentication():
    st.stop()

# Get connection
conn = get_connection()
database, schema = get_client_database()

cursor = conn.cursor()
cursor.execute(f"USE DATABASE {database}")
cursor.execute(f"USE SCHEMA {schema}")

# Header
st.title("📊 Dashboard")
user_info = st.session_state.get('user_info', {})
st.markdown(f"**{user_info.get('client_name', 'Client')}** - Real-time Analytics")

st.divider()

# Project selector
cursor.execute("SELECT project_id, project_name, project_type, status FROM PROJECTS ORDER BY created_at DESC")
projects = cursor.fetchall()

if not projects:
    st.warning("No projects found. Create your first project to get started!")
    st.stop()

project_options = {f"{p[1]} ({p[2]})": p[0] for p in projects}
selected_project = st.selectbox("📍 Select Project", list(project_options.keys()))
project_id = project_options[selected_project]

st.divider()

# Get project details
cursor.execute("""
    SELECT 
        project_name, address, project_type, status,
        purchase_date, purchase_price,
        total_spent_ci, total_spent_mi
    FROM PROJECTS 
    WHERE project_id = %s
""", (project_id,))

project = cursor.fetchone()

if not project:
    st.error("Project not found!")
    st.stop()

project_name, address, proj_type, status, purchase_date, purchase_price, spent_ci, spent_mi = project

# Calculate metrics
total_spent = (spent_ci or 0) + (spent_mi or 0)
days_active = (datetime.now().date() - purchase_date).days if purchase_date else 0
ci_percentage = (spent_ci / total_spent * 100) if total_spent > 0 else 0

# Top KPI Cards
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="Purchase Price",
        value=f"${purchase_price:,.0f}" if purchase_price else "N/A"
    )

with col2:
    st.metric(
        label="Total Invested",
        value=f"${total_spent:,.0f}",
        delta=f"${total_spent - (purchase_price or 0):,.0f} over purchase"
    )

with col3:
    st.metric(
        label="Cash Invested (CI)",
        value=f"${spent_ci:,.0f}" if spent_ci else "$0",
        delta=f"{ci_percentage:.1f}%"
    )

with col4:
    st.metric(
        label="Financed (MI)",
        value=f"${spent_mi:,.0f}" if spent_mi else "$0",
        delta=f"{100-ci_percentage:.1f}%"
    )

with col5:
    st.metric(
        label="Days Active",
        value=days_active,
        delta=f"{days_active/30:.1f} months"
    )

st.divider()

# Two column layout
left_col, right_col = st.columns([3, 2])

with left_col:
    # Spending by Category
    st.subheader("💰 Spending by Category")
    
    cursor.execute("""
        SELECT 
            COALESCE(category, 'Uncategorized') as category,
            SUM(amount) as total,
            COUNT(*) as count
        FROM EXPENSES
        WHERE project_id = %s
        GROUP BY category
        ORDER BY total DESC
    """, (project_id,))
    
    category_data = cursor.fetchall()
    
    if category_data:
        df_categories = pd.DataFrame(category_data, columns=['Category', 'Total', 'Count'])
        df_categories['Total'] = pd.to_numeric(df_categories['Total'], errors='coerce').round(2)
        df_categories['Percentage'] = (df_categories['Total'] / df_categories['Total'].sum() * 100).round(1)
        
        # Bar chart
        st.bar_chart(df_categories.set_index('Category')['Total'])
        
        # Data table
        st.dataframe(
            df_categories.style.format({
                'Total': '${:,.2f}',
                'Percentage': '{:.1f}%'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No expenses yet. Start adding expenses to see breakdown!")

with right_col:
    # CI vs MI Pie Chart
    st.subheader("💵 CI vs MI Split")
    
    cursor.execute("""
        SELECT 
            investment_type,
            SUM(amount) as total
        FROM EXPENSES
        WHERE project_id = %s
        GROUP BY investment_type
    """, (project_id,))
    
    ci_mi_data = cursor.fetchall()
    
    if ci_mi_data:
        df_ci_mi = pd.DataFrame(ci_mi_data, columns=['Type', 'Amount'])
        
        # Create percentage display
        total = df_ci_mi['Amount'].sum()
        
        for idx, row in df_ci_mi.iterrows():
            pct = (row['Amount'] / total * 100)
            st.metric(
                label=f"{'Cash Investment' if row['Type'] == 'CI' else 'Maintenance/Financed'}",
                value=f"${row['Amount']:,.2f}",
                delta=f"{pct:.1f}% of total"
            )
        
        st.divider()
        
        # Top Vendors
        st.subheader("🏢 Top Vendors")
        
        cursor.execute("""
            SELECT 
                vendor_name,
                COUNT(*) as transactions,
                SUM(amount) as total
            FROM EXPENSES
            WHERE project_id = %s
            GROUP BY vendor_name
            ORDER BY total DESC
            LIMIT 5
        """, (project_id,))
        
        vendor_data = cursor.fetchall()
        
        if vendor_data:
            for vendor, count, total in vendor_data:
                st.metric(
                    label=vendor or "Unknown",
                    value=f"${total:,.2f}",
                    delta=f"{count} payments"
                )
    else:
        st.info("No expense data yet!")

st.divider()

# Timeline Chart
st.subheader("📈 Spending Timeline")

cursor.execute("""
    SELECT 
        expense_date,
        SUM(amount) as daily_total,
        investment_type
    FROM EXPENSES
    WHERE project_id = %s
    GROUP BY expense_date, investment_type
    ORDER BY expense_date
""", (project_id,))

timeline_data = cursor.fetchall()

if timeline_data:
    df_timeline = pd.DataFrame(timeline_data, columns=['Date', 'Amount', 'Type'])
    
    # Pivot for stacked chart
    df_pivot = df_timeline.pivot_table(
        index='Date',
        columns='Type',
        values='Amount',
        aggfunc='sum',
        fill_value=0
    )
    
    st.area_chart(df_pivot)
    
    # Cumulative spending
    st.subheader("📊 Cumulative Spending")
    
    cursor.execute("""
        SELECT 
            expense_date,
            amount,
            SUM(amount) OVER (ORDER BY expense_date) as cumulative
        FROM EXPENSES
        WHERE project_id = %s
        ORDER BY expense_date
    """, (project_id,))
    
    cumulative_data = cursor.fetchall()
    df_cumulative = pd.DataFrame(cumulative_data, columns=['Date', 'Amount', 'Cumulative'])
    
    st.line_chart(df_cumulative.set_index('Date')['Cumulative'])
else:
    st.info("No timeline data yet!")

st.divider()

# Recent Transactions
st.subheader("📋 Recent Transactions")

cursor.execute("""
    SELECT 
        expense_date,
        description,
        vendor_name,
        category,
        amount,
        investment_type
    FROM EXPENSES
    WHERE project_id = %s
    ORDER BY expense_date DESC
    LIMIT 10
""", (project_id,))

recent = cursor.fetchall()

if recent:
    df_recent = pd.DataFrame(recent, columns=[
        'Date', 'Description', 'Vendor', 'Category', 'Amount', 'CI/M'
    ])
    
    st.dataframe(
        df_recent.style.format({
            'Amount': '${:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No transactions yet!")

cursor.close()

# Footer
st.divider()
st.caption("FlipTrack AI - Real-time data from Snowflake")
