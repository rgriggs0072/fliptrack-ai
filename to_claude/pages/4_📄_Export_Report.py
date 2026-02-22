"""
FlipTrack AI - Export Report (AI-Generated Excel)
=================================================
AI generates professional investor-ready Excel reports with client branding.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

sys.path.append(str(Path(__file__).parent.parent))

from utils.auth import check_authentication
from utils.snowflake_connection import get_connection, get_client_database
from utils.branding import get_brand, apply_custom_css

# Load brand
brand = get_brand("kituwah_properties")

# Page config
st.set_page_config(
    page_title=f"Export Report - {brand['company']}",
    page_icon="📄",
    layout="wide"
)

# Apply branding
apply_custom_css(brand)

# Check authentication
if not check_authentication():
    st.stop()

# Header
st.title("📄 Export Report")
st.markdown("Generate professional Excel reports with AI")

st.divider()

# Get connection
conn = get_connection()
database, schema = get_client_database()

cursor = conn.cursor()
cursor.execute(f"USE DATABASE {database}")
cursor.execute(f"USE SCHEMA {schema}")

# Project selector
cursor.execute("SELECT project_id, project_name FROM PROJECTS ORDER BY created_at DESC")
projects = cursor.fetchall()

if not projects:
    st.warning("No projects found!")
    st.stop()

project_options = {p[1]: p[0] for p in projects}
selected_project = st.selectbox("📍 Select Project", list(project_options.keys()))
project_id = project_options[selected_project]

st.divider()

# Report options
st.subheader("⚙️ Report Options")

col1, col2 = st.columns(2)

with col1:
    report_type = st.selectbox(
        "Report Type",
        ["Investment Summary", "Detailed Expense Report", "Investor Package", "Tax Report"]
    )

with col2:
    include_charts = st.checkbox("Include Charts", value=True)

# Generate button
st.divider()

if st.button("🚀 Generate Excel Report", type="primary", width="stretch"):
    
    with st.spinner("🤖 AI is generating your professional report..."):
        
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
        project_name, address, proj_type, status, purchase_date, purchase_price, spent_ci, spent_mi = project
        
        # Get all expenses
        cursor.execute("""
            SELECT 
                expense_date, description, vendor_name, category,
                amount, investment_type
            FROM EXPENSES
            WHERE project_id = %s
            ORDER BY expense_date
        """, (project_id,))
        
        expenses = cursor.fetchall()
        df_expenses = pd.DataFrame(expenses, columns=[
            'Date', 'Description', 'Vendor', 'Category', 'Amount', 'CI/M'
        ])
        
        # Get category summary
        cursor.execute("""
            SELECT 
                category,
                SUM(amount) as total,
                COUNT(*) as count
            FROM EXPENSES
            WHERE project_id = %s
            GROUP BY category
            ORDER BY total DESC
        """, (project_id,))
        
        categories = cursor.fetchall()
        df_categories = pd.DataFrame(categories, columns=['Category', 'Total', 'Count'])
        
        # Get CI/M breakdown
        cursor.execute("""
            SELECT 
                investment_type,
                SUM(amount) as total,
                COUNT(*) as count
            FROM EXPENSES
            WHERE project_id = %s
            GROUP BY investment_type
        """, (project_id,))
        
        ci_mi = cursor.fetchall()
        df_ci_mi = pd.DataFrame(ci_mi, columns=['Type', 'Total', 'Count'])
        
        # Get vendor summary
        cursor.execute("""
            SELECT 
                vendor_name,
                COUNT(*) as payments,
                SUM(amount) as total
            FROM EXPENSES
            WHERE project_id = %s
            GROUP BY vendor_name
            ORDER BY total DESC
        """, (project_id,))
        
        vendors = cursor.fetchall()
        df_vendors = pd.DataFrame(vendors, columns=['Vendor', 'Payments', 'Total'])
        
        # Create Excel file
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            
            # Summary sheet with company branding
            summary_data = {
                'Metric': [
                    '=== COMPANY INFO ===',
                    'Company',
                    'Owner',
                    'Phone',
                    'Email',
                    'Tagline',
                    '',
                    '=== PROJECT INFO ===',
                    'Project Name',
                    'Address',
                    'Project Type',
                    'Status',
                    'Purchase Date',
                    'Purchase Price',
                    '',
                    '=== INVESTMENT SUMMARY ===',
                    'Total Invested',
                    'Capital Investment (CI)',
                    'Maintenance Investment (MI)',
                    '',
                    '=== PROJECT STATS ===',
                    'Total Expenses Logged',
                    'Number of Vendors',
                    'Days Active',
                    '',
                    'Report Generated'
                ],
                'Value': [
                    '',
                    brand['company'],
                    brand['contact']['owner'],
                    brand['contact']['phone'],
                    brand['contact']['email'],
                    brand['contact'].get('tagline', ''),
                    '',
                    '',
                    project_name,
                    address or 'N/A',
                    proj_type,
                    status,
                    purchase_date.strftime('%Y-%m-%d') if purchase_date else 'N/A',
                    f'${purchase_price:,.2f}' if purchase_price else 'N/A',
                    '',
                    '',
                    f'${(spent_ci or 0) + (spent_mi or 0):,.2f}',
                    f'${spent_ci:,.2f} ({spent_ci / ((spent_ci or 0) + (spent_mi or 1)) * 100:.1f}%)' if spent_ci else '$0',
                    f'${spent_mi:,.2f} ({spent_mi / ((spent_ci or 1) + (spent_mi or 0)) * 100:.1f}%)' if spent_mi else '$0',
                    '',
                    '',
                    len(df_expenses),
                    len(df_vendors),
                    (datetime.now().date() - purchase_date).days if purchase_date else 0,
                    '',
                    datetime.now().strftime('%Y-%m-%d %H:%M')
                ]
            }
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Executive Summary', index=False)
            
            # All expenses
            df_expenses.to_excel(writer, sheet_name='All Expenses', index=False)
            
            # Category breakdown
            df_categories.to_excel(writer, sheet_name='By Category', index=False)
            
            # CI/M Analysis
            df_ci_mi.to_excel(writer, sheet_name='CI vs MI', index=False)
            
            # Vendor payments
            df_vendors.to_excel(writer, sheet_name='Vendors', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Success message
        st.success("✅ Report Generated Successfully!")
        
        # Download button
        st.download_button(
            label="📥 Download Excel Report",
            data=output,
            file_name=f"FlipTrack_Report_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            width="stretch"
        )
        
        # Show preview
        st.divider()
        st.subheader("📊 Report Preview")
        
        tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Expenses", "Categories", "Vendors"])
        
        with tab1:
            st.dataframe(df_summary, width="stretch", hide_index=True)
        
        with tab2:
            st.dataframe(df_expenses, width="stretch", hide_index=True)
        
        with tab3:
            st.dataframe(df_categories, width="stretch", hide_index=True)
        
        with tab4:
            st.dataframe(df_vendors, width="stretch", hide_index=True)

cursor.close()

# Footer
st.divider()
st.caption("FlipTrack AI - Professional Reports in Seconds")
